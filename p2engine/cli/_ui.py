from rich.console import Console

# One console object for the whole CLI
console = Console()

# Central place for colour / style names
STYLES = {
    "header": "bold magenta",
    "name": "cyan",
    "value": "white",
    "timestamp": "green",
    "kind": "magenta",
    "content": "white",
}
