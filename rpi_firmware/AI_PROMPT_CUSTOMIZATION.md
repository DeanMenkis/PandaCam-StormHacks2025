# AI Prompt Customization Guide

## Overview
The AI analysis prompt and settings are stored in `ai_config.json` for easy customization without editing the main Python code.

## Configuration File: `ai_config.json`

### Gemini Settings
- **`prompt`**: The text prompt sent to the AI with each image
- **`temperature`**: Controls randomness (0.0 = deterministic, 1.0 = very random)
- **`max_output_tokens`**: Maximum length of AI response (50-500 recommended)
- **`top_p`**: Controls diversity of word choices (0.1-1.0)
- **`top_k`**: Limits vocabulary to top K words (1-100)

### Analysis Settings
- **`timeout_seconds`**: How long to wait for AI response (10-30 recommended)
- **`retry_attempts`**: Number of retries on failure (1-3)
- **`fallback_enabled`**: Whether to show fallback message on failure

### UI Settings
- **`show_technical_details`**: Show detailed API information
- **`log_ai_requests`**: Log AI requests to system log
- **`display_token_usage`**: Show token usage in UI

## Example Prompts

### Basic 3D Print Analysis
```json
"prompt": "Analyze this 3D printer image. Report on print quality, layer adhesion, and any visible defects. Be concise."
```

### Detailed Technical Analysis
```json
"prompt": "Examine this 3D print image and provide detailed feedback on:\n1. Layer quality and adhesion\n2. Print bed condition\n3. Filament flow issues\n4. Mechanical problems\n5. Overall print success probability\n\nBe specific and technical."
```

### Simple Description
```json
"prompt": "Describe what you see in this image in 2-3 sentences."
```

## How to Customize

1. **Edit the prompt**: Open `ai_config.json` and modify the `"prompt"` field
2. **Adjust settings**: Change temperature, tokens, etc. as needed
3. **Save the file**: The app will automatically load changes on next restart
4. **Test**: Take a photo to see how the AI responds with your new prompt

## Tips for Good Prompts

- **Be specific**: Tell the AI exactly what to look for
- **Set expectations**: Specify the format and length you want
- **Use context**: Mention this is a 3D printer monitoring system
- **Keep it concise**: Shorter prompts often work better
- **Test iteratively**: Try different prompts to see what works best

## Troubleshooting

- If the config file is missing, the app uses default settings
- Invalid JSON will cause the app to use defaults
- Check the system log for configuration loading messages
- Restart the app after making changes to the config file
