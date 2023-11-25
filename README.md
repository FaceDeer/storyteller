# storyteller
A simple framework for using a local Koboldcpp LLM to help with story-writing

This application uses PyQt to provide an interface to a local [Koboldcpp](https://github.com/LostRuins/koboldcpp) instance that's designed to make story-writing easier to keep organized and make good use of a smaller context size than the story can fit into.

It divides the story up into chapters, and scenes within those chapters, and when generating the text for scenes it combines the text and summaries of previous scenes and chapters to hopefully provide the salient details needed for the current scene to generate well.
