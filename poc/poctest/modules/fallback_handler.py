def handle_fallback(user_input, suggestions=None):
    if suggestions:
        response = "Sorry, I couldn't understand your request. Did you mean:\n"
        for i, suggestion in enumerate(suggestions, 1):
            response += f"{i}. {suggestion}\n"
        response += "Please enter the number of your choice:"
        print(response)
        
        try:
            choice = int(input().strip())
            if 1 <= choice <= len(suggestions):
                return suggestions[choice - 1]
            else:
                return "Invalid choice. Please try again."
        except ValueError:
            return "Invalid input. Please enter a number."
    else:
        return "Sorry, I couldn't understand your request. Could you rephrase it?"
