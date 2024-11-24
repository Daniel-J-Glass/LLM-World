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
### Interactable LLM Driven Text2Video Generation
https://github.com/user-attachments/assets/4b400332-cd6e-44e4-b3b7-a689401ab0ba

#### Actions taken (turn-by-turn text-based actions)
 1) "Walk through forest"
 2) "See moss and go pick it up"
 3) "Pull out my axe and try to chop a crystal tree down"

#### Current limitations
 1) Text2Video model (Runway Gen-3 Alpha Turbo) is either not coherent enough OR model needs to be prompted to more effectively use (currently working on prompt tuning the LLM to use Text2Video models better)
    - Will upgrade to generating a start AND end image at some point. Right now, the end image has no way of being logically tied to the start image, so I can't generate it independently
    - Once OpenAI releases LLM native image generation (I think the term was LLVM, I don't recall), the LLM should provide a much more coherent way of creating an end image based on the user action. Then we can just use Text2Video to fill in between.
 3) Using the last frame of a video tends toward decoherence of realistic video
    - Working on implementing an img2img refinement step on the final frame for each step. This should keep image style roughly persistent
 5) Generation times are slow (will switch to faster services when available)

### LLM Anchored Image Generation
By using LLM to output SVG, we provide a logical "grounding" to the scene. This SVG is consistent for the scene, meaning any interactions with the scene will update the SVG, guiding the image generated.

![LLM Image Generation](examples/Developer_GUI.png)

## Examples
### Web App GUI
![Web App GUI](examples/GUI_Room.png)


