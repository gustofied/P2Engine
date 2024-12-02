import os
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import faiss
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForCausalLM
from tqdm import tqdm

# Set the device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Set random seeds for reproducibility
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)
if device.type == 'cuda':
    torch.cuda.manual_seed_all(42)

# Define paths to the ARC dataset
arc_dataset_path = 'data/training'

# Function to load ARC tasks
def load_arc_tasks(task_dir):
    tasks = []
    for filename in os.listdir(task_dir):
        if filename.endswith('.json'):
            with open(os.path.join(task_dir, filename), 'r') as f:
                task = json.load(f)
                tasks.append(task)
    return tasks

# Load all tasks
all_tasks = load_arc_tasks(arc_dataset_path)
print(f"Total tasks loaded: {len(all_tasks)}")

# Shuffle the tasks
random.shuffle(all_tasks)

# Split into training and testing sets
split_ratio = 0.8
split_index = int(split_ratio * len(all_tasks))
train_tasks = all_tasks[:split_index]
test_tasks = all_tasks[split_index:]

print(f"Training tasks: {len(train_tasks)}")
print(f"Testing tasks: {len(test_tasks)}")

# Define maximum grid size
MAX_GRID_SIZE = 30

# Function to preprocess grids
def preprocess_grid(grid, max_size=MAX_GRID_SIZE):
    processed_grid = np.zeros((max_size, max_size), dtype=np.int64)
    for i, row in enumerate(grid):
        for j, cell in enumerate(row):
            if i < max_size and j < max_size:
                processed_grid[i, j] = cell
    return processed_grid

# Build a set of all symbols used in the dataset
symbols = set()
for task in train_tasks:
    for example in task['train']:
        symbols.update(sum(example['input'], []))
        symbols.update(sum(example['output'], []))

symbol_to_int = {symbol: idx for idx, symbol in enumerate(sorted(symbols))}
int_to_symbol = {idx: symbol for symbol, idx in symbol_to_int.items()}
num_symbols = len(symbol_to_int)
print(f"Total unique symbols: {num_symbols}")

# Define the GridEncoder model
class GridEncoder(nn.Module):
    def __init__(self, embedding_dim=128, num_symbols=num_symbols):
        super(GridEncoder, self).__init__()
        self.embedding_dim = embedding_dim
        self.embedding = nn.Embedding(num_symbols, 16)
        self.conv_layers = nn.Sequential(
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )
        self.fc = nn.Linear(64 * 7 * 7, embedding_dim)

    def forward(self, x):
        x = self.embedding(x).permute(0, 3, 1, 2)
        x = self.conv_layers(x)
        x = x.contiguous().view(x.size(0), -1)
        return self.fc(x)

# Create the TripletGridDataset
class TripletGridDataset(Dataset):
    def __init__(self, tasks):
        self.samples = []
        for task in tasks:
            for example in task['train']:
                input_grid = preprocess_grid(example['input'])
                output_grid = preprocess_grid(example['output'])
                self.samples.append((input_grid, output_grid))

        # Create negatives by shuffling outputs
        self.negatives = [out for _, out in self.samples]
        random.shuffle(self.negatives)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        anchor, positive = self.samples[idx]
        negative = self.negatives[idx]

        anchor_tensor = torch.tensor(anchor, dtype=torch.long)
        positive_tensor = torch.tensor(positive, dtype=torch.long)
        negative_tensor = torch.tensor(negative, dtype=torch.long)

        return anchor_tensor, positive_tensor, negative_tensor

# Instantiate the dataset and DataLoader
triplet_dataset = TripletGridDataset(train_tasks)
triplet_loader = DataLoader(triplet_dataset, batch_size=8, shuffle=True)

# Initialize the encoder
encoder = GridEncoder().to(device)

# Define loss function and optimizer
criterion = nn.TripletMarginLoss(margin=1.0)
optimizer = optim.Adam(encoder.parameters(), lr=1e-3)

# Training loop
num_epochs = 3
for epoch in range(num_epochs):
    encoder.train()
    total_loss = 0
    for anchor, positive, negative in tqdm(triplet_loader, desc=f"Epoch {epoch + 1}/{num_epochs}"):
        anchor, positive, negative = anchor.to(device), positive.to(device), negative.to(device)

        optimizer.zero_grad()
        anchor_emb = encoder(anchor)
        positive_emb = encoder(positive)
        negative_emb = encoder(negative)
        loss = criterion(anchor_emb, positive_emb, negative_emb)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    print(f"Epoch {epoch + 1}, Loss: {total_loss / len(triplet_loader)}")

# Encode training grids
encoder.eval()
embeddings = []
grid_indices = []
for task_idx, task in enumerate(train_tasks):
    for example_idx, example in enumerate(task['train']):
        input_grid = preprocess_grid(example['input'])
        embeddings.append(encoder(torch.tensor(input_grid, dtype=torch.long).unsqueeze(0).to(device)).cpu().detach().numpy())
        grid_indices.append((task_idx, example_idx))

embeddings = np.vstack(embeddings).astype('float32')
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

# Load LLaMA model
model_name = "NousResearch/Nous-Hermes-2-Mistral-7B-DPO"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name).to(device)

# Define helpers for testing
def grid_to_text(grid):
    return "\n".join(" ".join(map(str, row)) for row in grid)

def retrieve_similar_examples(input_grid, k=4):
    input_emb = encoder(torch.tensor(preprocess_grid(input_grid), dtype=torch.long).unsqueeze(0).to(device)).cpu().detach().numpy()
    _, indices = index.search(input_emb, k)
    similar_examples = []
    for idx in indices[0]:
        task_idx, example_idx = grid_indices[idx]
        similar_examples.append({
            "input": train_tasks[task_idx]['train'][example_idx]['input'],
            "output": train_tasks[task_idx]['train'][example_idx]['output'],
        })
    return similar_examples

def create_prompt(similar_examples, input_grid):
    prompt = "Below are examples of input and output transformations:\n\n"
    for example in similar_examples:
        prompt += f"Input:\n{grid_to_text(example['input'])}\n"
        prompt += f"Output:\n{grid_to_text(example['output'])}\n\n"
    prompt += f"Given the following input grid:\n{grid_to_text(input_grid)}\n"
    prompt += "What is the expected output grid?"
    return prompt

def generate_output(prompt):
    input_ids = tokenizer(prompt, return_tensors="pt", truncation=True, padding=True).to(device)['input_ids']
    output_ids = model.generate(input_ids, max_new_tokens=100, early_stopping=True)
    return tokenizer.decode(output_ids[0], skip_special_tokens=True)

# Testing
test_task = test_tasks[0]
test_example = test_task['test'][0]
similar_examples = retrieve_similar_examples(test_example['input'])
prompt = create_prompt(similar_examples, test_example['input'])
output = generate_output(prompt)
print("Generated Output:", output)
