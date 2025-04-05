# Creating User Content for Asobann

This guide explains how to create custom games and content for the Asobann online board game platform.

## Table of Contents

1. [Overview](#overview)
2. [Kit Structure](#kit-structure)
3. [Components](#components)
4. [Adding Images](#adding-images)
5. [Organization](#organization)
6. [Example Kit](#example-kit)

## Overview

Asobann is a flexible platform for creating and playing various tabletop games online. User content in Asobann is organized as "kits" - complete game definitions including all components, their properties, and initial layout.

Each kit is defined using a JSON file, which can be placed in the `asobann_contents/kit/` directory. More complex kits can have their own subdirectory with associated image assets.

## Kit Structure

A kit JSON file has the following top-level structure:

```json
{
  "kit": {
    "name": "Game Name",
    "label": "Game Name",
    "label_ja": "ゲーム名 (Japanese name)",
    "height": "64px",
    "width": "64px",
    "boxAndComponents": {
      // Components organization
    },
    "usedComponentNames": [
      // List of all component names
    ]
  },
  "components": [
    // Detailed component definitions
  ]
}
```

### Key properties:

- `name`: Internal identifier for the kit
- `label`/`label_ja`: Display names in English and Japanese
- `height`/`width`: Default dimensions for the kit box
- `boxAndComponents`: Defines how components are organized in the box
- `usedComponentNames`: List of all component names used in the kit
- `components`: Detailed definitions of each game component

## Components

Components are the building blocks of your game (cards, boards, tokens, etc.). Each component has properties that define its appearance and behavior.

Common component properties:

```json
{
  "name": "Component Name",
  "text": "Text on component (English)",
  "text_ja": "Text on component (Japanese)",
  "color": "cyan",
  "textColor": "black",
  "top": "20px",
  "left": "100px",
  "height": "80px",
  "width": "60px",
  "draggable": true,
  "flippable": true,
  "faceup": false,
  "traylike": false,
  "handArea": false
}
```

### Special Component Types:

1. **Cards**:
   - Use `flippable: true` for cards that can be turned over
   - Define `faceupText` and `facedownText` for different sides
   - Set `faceup: false` to start cards face down

2. **Card Containers**:
   - Use `traylike: true` for components that hold cards
   - Include `cardistry` property with actions like "spread out", "collect", "flip all", "shuffle"

3. **Hand Areas**:
   - Use `handArea: true` to create player-specific areas
   - Cards in hand areas are only visible to their owner

## Adding Images

For games that require images:

1. Create a subdirectory in `asobann_contents/kit/` for your game
2. Add an `images/` folder within your game directory
3. Place all image files in the `images/` folder
4. Reference images in your components by adding `imageUrl` property pointing to the relative path

**Note**: The platform currently supports PNG and JPG images.

## Organization

For simple games with few components, a single JSON file may be sufficient. For complex games:

1. Create a dedicated subdirectory (e.g., `asobann_contents/kit/my_game/`)
2. Place the main JSON file inside this directory (e.g., `my_game.json`)
3. Add an `images/` subdirectory for all game images
4. You can use helper scripts (like CSV converters) to generate components

## Example Kit

A minimal example of a simple card game:

```json
{
  "kit": {
    "name": "Simple Cards",
    "label": "Simple Cards",
    "label_ja": "シンプルカード",
    "height": "64px",
    "width": "64px",
    "boxAndComponents": {
      "Deck": [
        "Card A",
        "Card B",
        "Card C"
      ]
    },
    "usedComponentNames": [
      "Deck", "Card A", "Card B", "Card C"
    ]
  },
  "components": [
    {
      "name": "Deck",
      "color": "black",
      "top": "20px",
      "left": "20px",
      "height": "100px",
      "width": "80px",
      "draggable": true,
      "traylike": true,
      "cardistry": ["spread out", "collect", "shuffle"]
    },
    {
      "name": "Card A",
      "faceupText": "A",
      "facedownText": "Card",
      "color": "white",
      "textColor": "black",
      "height": "100px",
      "width": "80px",
      "draggable": true,
      "flippable": true,
      "faceup": false
    },
    {
      "name": "Card B",
      "faceupText": "B",
      "facedownText": "Card",
      "color": "white",
      "textColor": "black",
      "height": "100px",
      "width": "80px",
      "draggable": true,
      "flippable": true,
      "faceup": false
    },
    {
      "name": "Card C",
      "faceupText": "C",
      "facedownText": "Card",
      "color": "white",
      "textColor": "black",
      "height": "100px",
      "width": "80px",
      "draggable": true,
      "flippable": true,
      "faceup": false
    }
  ]
}
```

For more complex examples, see the existing games in the `asobann_contents/kit/` directory, such as "100 Narabe", "The Kanban Game", or "Win by Team".