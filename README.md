# LLM World
 Visual narrative adventure powered by Claude 3.5

## Instructions
 1) From root dir, run ```pip install -r requirments.txt```
 2) Run ```python -m src.app```
 3) To start a new adventure, delete:
    - ```game_state.json```
    - ```world_map.json```
    - ```world_state.json```

## Novel Ideas
### Interactable LLM Driven Video Generation
https://github.com/user-attachments/assets/4b400332-cd6e-44e4-b3b7-a689401ab0ba

## Actions taken (turn-by-turn text-based actions)
1) Walk through forest
2) See moss and go pick it up
3) Pull out my axe and try to chop a crystal tree down

## Current limitations
1) Text2Video model (Runway Gen-3 Alpha Turbo) is either not coherent enough OR model needs to be prompted to more effectively use (currently working on prompt tuning the LLM to use Text2Video models better)
2) Using the last frame of a video tends toward decoherence of realistic video (to be alleviated with img2img refinement step on the final frame for each step)
3) Generation times are slow

### LLM Anchored Image Generation
By using LLM to output SVG, we provide a logical "grounding" to the scene. This SVG is consistent for the scene, meaning any interactions with the scene will update the SVG, guiding the image generated.

![LLM Image Generation](examples/Developer_GUI.png)

## Examples
### Web App GUI
![Web App GUI](examples/GUI_Room.png)


