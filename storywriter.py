import requests
import json
import re
import sys

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QFormLayout, QGridLayout, QFileDialog, QFrame, QScrollArea, QSizePolicy


def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("catched:", tb)
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

exportedStylesheet = "background-color: rgb(252, 245, 229);"

# Define the URL
generateUrl = "http://localhost:5001/api/v1/generate"
tokenCountUrl = "http://localhost:5001/api/extra/tokencount"

# Define the headers for the request
headers = {
    'Content-Type': 'application/json'
}

def getPromptJson(prompt, grammar):
    data = {
        "prompt": prompt,
        "max_length": 1024
        #"stop_sequence": "</s>"
    }
    if grammar:
        data["grammar"] = grammar
    return json.dumps(data)

def getResult(prompt, grammar):
    # Send the request and get the response
    response = requests.post(generateUrl, headers=headers, data=getPromptJson(prompt, grammar))
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the response JSON into a Python dictionary
        response_data = json.loads(response.text)
        #print(response_data)
        return response_data["results"][0]["text"].strip()
    else:
        print(f"Request failed with status code {response.status_code}")
        return False

def countTokens(prompt):
    response = requests.post(tokenCountUrl, headers=headers, data=json.dumps({"prompt":prompt}))
    if response.status_code == 200:
        # Parse the response JSON into a Python dictionary
        response_data = json.loads(response.text)
        print(response_data)

def sanitize_filename(filename):
    return re.sub(r'(?u)[^-\w.]', '_', filename)

def clear_layout(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget() is not None:
            child.widget().deleteLater()
        elif child.layout() is not None:
            clear_layout(child.layout())

def findLayoutInParent(parentLayout, childLayout):
    for i in range(parentLayout.count()):
        layout_item = parentLayout.itemAt(i)
        if layout_item.layout() == childLayout:
            return i
            break
    return None


class EmptyFlaggedLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the initial stylesheet
        self.update_stylesheet()

    def update_stylesheet(self):
        if len(self.text()) > 0:
            # If the text is set, use a default border
            self.setStyleSheet("border: 1px solid black")
        else:
            # If the text is not set, use a red border
            self.setStyleSheet("border: 1px solid red")

    def setText(self, text):
        super().setText(text)
        self.update_stylesheet()

class EmptyFlaggedTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set the initial stylesheet
        self.update_stylesheet()

    def update_stylesheet(self):
        if len(self.toPlainText()) > 0:
            # If the text is set, use a default border
            self.setStyleSheet("border: 1px solid black")
        else:
            # If the text is not set, use a red border
            self.setStyleSheet("border: 1px solid red")

    def setPlainText(self, text):
        super().setPlainText(text)
        self.update_stylesheet()


#Note to self: update Scene to have a root widget rather than adding things directly to its layout
class Scene:
    def __init__(self, parentChapter, sceneData=None):
        self.parentChapter = parentChapter
        self.layout = QVBoxLayout()
        self.parentChapter.scenes.append(self)
        self.parentChapter.scenesLayout.addLayout(self.layout)

        self.textLayout = QGridLayout()
        self.summary = QTextEdit()
        self.summary.setPlaceholderText("Scene Summary")
        self.summary.setMinimumHeight(100)
        self.textLayout.addWidget(QLabel("Scene Summary"),0,0)
        self.textLayout.addWidget(self.summary,1,0)

        self.summary.setToolTip("""This text is sent to the LLM to tell it what this scene is supposed to depict.
It is also used when generating later scenes in this chapter as part of the summary of how the chapter has progressed to this point.""")

        self.text = QTextEdit()
        self.text.setPlaceholderText("Text")
        self.text.setStyleSheet(exportedStylesheet)
        self.textLayout.addWidget(QLabel("Text"),0,1)
        self.textLayout.addWidget(self.text,1,1)

        self.text.setToolTip("""This is the finished output text for this story.""")

        self.layout.addLayout(self.textLayout)
        
        buttons = QHBoxLayout()

        self.generate_button = QPushButton('Generate text of this scene')
        self.generate_button.clicked.connect(self.generateScene)
        buttons.addWidget(self.generate_button)

        self.delete_button = QPushButton('Remove this scene')
        self.delete_button.clicked.connect(self.deleteScene)
        buttons.addWidget(self.delete_button)

        self.layout.addLayout(buttons)

        if sceneData:
            self.summary.setPlainText(sceneData["summary"])
            self.text.setPlainText(sceneData["text"])

    def deleteScene(self):
        parentLayout = self.parentChapter.scenesLayout
        index = findLayoutInParent(parentLayout, self.layout)
        if index is None:
            return
        layout_item = parentLayout.takeAt(index)
        clear_layout(layout_item)
        del layout_item
        del self.parentChapter.scenes[index]
        self.parentChapter.parentStory.update()
        return

    def generateScene(self):
        scene = self
        chapter = scene.parentChapter
        story = chapter.parentStory
        chapter_index = None
        scene_index = None
        for i in range(len(story.chapters)):
            if story.chapters[i] == chapter:
                chapter_index= i
                break
        for i in range(len(chapter.scenes)):
            if chapter.scenes[i] == scene:
                scene_index = i
                break

        print("chapter index " + str(chapter_index))
        print("scene index " + str(scene_index))

        prompt = "{{[INPUT]}}\nYou are to take the role of an author writing a story. The story is titled \"" + story.title.text() + "\"."
        if len(story.summary.toPlainText()) > 0:
            prompt = prompt + "\n\nGeneral background information: " + story.summary.toPlainText()
        prompt = prompt + "\n\nThe story so far has had the following major events happen:"
        for c in range(chapter_index + 1):
            chapter = story.chapters[c]
            prompt = prompt + "\n\n" + chapter.summary.toPlainText()
        prompt = prompt + "\n\nThe current chapter is titled \"" + chapter.title.text() + "\""
        if scene_index > 1:
            prompt = prompt + "\n\nThe following scenes have already happened in this chapter:"
            for s in range(scene_index-1):
                prompt = prompt + "\n" + chapter.scenes[s].summary.toPlainText()
        if scene_index > 0:
            prompt = prompt +"\n\nThe most recent scene before this one was:\n\n" + chapter.scenes[scene_index-1].text.toPlainText()

        prompt = prompt + "\n\nYou are now writing the next scene in which the following occurs: " + scene.summary.toPlainText() \
                 + "\n\nPlease write out this scene.\n{{[OUTPUT]}}"

        print(prompt)
        scene.text.setPlainText(getResult(prompt, None))
        return

class Chapter:
    def __init__(self, parentStory, chapterData=None):
        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Box)
        self.frame.setLineWidth(1)
        self.layout = QVBoxLayout()
        self.frame.setLayout(self.layout)
        self.parentStory = parentStory
        self.parentStory.chapters.append(self)
        
        title = QFormLayout()

        self.title = QLineEdit()
        self.title.setPlaceholderText('Chapter Title')
        self.title.setStyleSheet(exportedStylesheet)
        title.addRow('Chapter Title:', self.title)

        self.layout.addLayout(title)

        self.summary = QTextEdit()
        self.summary.setPlaceholderText('Previous Chapter Summary')
        self.summary.setMinimumHeight(100)
        self.summary.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summaryLabel = QLabel('Summary of the\nprevious chapter:')
        generate_previous_button = QPushButton("Generate summary\nof previous chapter")
        generate_previous_button.clicked.connect(self.generateSummary)

        summaryContainer = QWidget()
        summaryContainerLayout = QGridLayout()
        summaryContainer.setLayout(summaryContainerLayout)
        summaryContainerLayout.addWidget(summaryLabel,0,0)
        summaryContainerLayout.addWidget(generate_previous_button,1,0)
        summaryContainerLayout.addWidget(self.summary,0,1,2,1)

        summaryContainer.setToolTip("""The summary of the previous chapter is used when prompting the LLM to provide it with context for how the story reached the current point.
Adding a summary of the "previous chapter" to the first chapter can be useful to provide background information that may not be relevant later in the story,
such as a description of how the characters got into the initial situation they first find themselves in.
You can use the AI to automatically generate a summary of the previous chapter's text, but it's good to review and edit it to ensure it focuses on what you consider important.""")
        
        self.layout.addWidget(summaryContainer)

        self.scenes = []
        self.scenesLayout = QVBoxLayout()
        self.scenesLayout.setContentsMargins(20,0,0,0)
        self.layout.addLayout(self.scenesLayout)

        buttons = QHBoxLayout()

        self.add_scene_button = QPushButton("Add a new scene to this chapter")
        self.add_scene_button.clicked.connect(self.addScene)
        buttons.addWidget(self.add_scene_button)


        self.delete_button = QPushButton('Remove this chapter')
        self.delete_button.clicked.connect(self.deleteChapter)
        buttons.addWidget(self.delete_button)

        self.layout.addLayout(buttons)

        if chapterData:
            self.title.setText(chapterData["title"])
            self.summary.setPlainText(chapterData["summary"])
            for sceneData in chapterData["scenes"]:
                Scene(self, sceneData)

        self.parentStory.scrollContentLayout.addWidget(self.frame)
        #self.parentStory.scrollContentLayout.update()
        self.parentStory.scrollContent.adjustSize()

    def deleteChapter(self):
        parentLayout = self.parentStory.scrollContentLayout
        parentLayout.removeWidget(self.frame)
        self.frame.deleteLater()
        self.parentStory.chapters.remove(self)
        self.parentStory.update()

    def addScene(self):
        Scene(self)

    def generateSummary(self):
        chapter = self
        story = chapter.parentStory
        chapter_index = None
        for i in range(len(story.chapters)):
            if story.chapters[i] == chapter:
                chapter_index = i
                break
        if chapter_index == 0:
            return ##Temporary hack, need to disable this button on the first chapter

        chapter_index = chapter_index - 1

        print("chapter index " + str(chapter_index))

        prompt = "{{[INPUT]}}\nYou are to take the role of an author writing a story. The story is titled \"" + story.title.text() + "\"."
        if len(story.summary.toPlainText()) > 0:
            prompt = prompt + "\nGeneral background information: " + story.summary.toPlainText()
        prompt = prompt + "\n\nThe most recent chapter of the story is:"
        for scene in story.chapters[chapter_index].scenes:
            prompt = prompt + "\n\n" + scene.text.toPlainText()

        prompt = prompt + "\n\nPlease summarize this chapter in 200 words or less, focusing on the information that's important for writing future scenes in this story.\n{{[OUTPUT]}}"

        print(prompt)
        chapter.summary.setPlainText(getResult(prompt, None))
        return

class StoryWriter(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Story writer')

        layout = QVBoxLayout()

        self.title = QLineEdit()
        self.title.setPlaceholderText('Title')
        self.title.setStyleSheet(exportedStylesheet)
        layout.addWidget(self.title)

        self.title.setToolTip("The title of the story. This is also currently used as the filename when saving or exporting the story.")

        summary = QWidget()
        summaryLayout = QFormLayout()
        self.summary = QTextEdit()
        self.summary.setPlaceholderText('Background Information')
        summaryLayout.addRow("Background\nInformation", self.summary)
        summary.setLayout(summaryLayout)
        summary.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        summary.setMaximumHeight(100)
        layout.addWidget(summary)

        summary.setToolTip("Background information is always added at the top of prompts sent to the LLM.")

        self.chapters = []

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)

        self.scrollContent = QWidget(self.scrollArea)
        self.scrollContentLayout = QVBoxLayout(self.scrollContent)
        self.scrollContent.setLayout(self.scrollContentLayout)
        self.scrollArea.setWidget(self.scrollContent)
        self.scrollArea.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        layout.addWidget(self.scrollArea)


        self.buttonsLayout = QHBoxLayout()

        self.new_chapter_button = QPushButton('Add a new Chapter')
        self.new_chapter_button.clicked.connect(self.addChapter)
        self.buttonsLayout.addWidget(self.new_chapter_button)

        self.save_button = QPushButton('Save')
        self.save_button.clicked.connect(self.saveStory)
        self.buttonsLayout.addWidget(self.save_button)
        self.save_button.setToolTip("Because the programmer is lazy this currently just saves the current story as a file called title.json")

        self.load_button = QPushButton('Load')
        self.load_button.clicked.connect(self.loadStory)
        self.buttonsLayout.addWidget(self.load_button)

        self.export_button = QPushButton('Export Text')
        self.export_button.clicked.connect(self.exportStory)
        self.buttonsLayout.addWidget(self.export_button)
        self.export_button.setToolTip("Exports the \"end product\" parts of the story as a text file. Summaries are removed.")

        layout.addLayout(self.buttonsLayout)

        self.setLayout(layout)

    def addChapter(self):
        Chapter(self)

    def loadStory(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName()
        jsonData = None
        with open(file_path, "r") as f:
            jsonData = json.load(f)
        if jsonData is None:
            return
        self.summary.setPlainText(jsonData["summary"])
        self.title.setText(jsonData["title"])
        self.chapters = []
        for widget in self.scrollContent.findChildren(QWidget):
            widget.deleteLater()
        self.scrollContentLayout.update()
        for chapterData in jsonData["chapters"]:
            Chapter(self, chapterData)

    def saveStory(self):
        filename = sanitize_filename(self.title.text())
        jsonData = {}
        jsonData["title"] = self.title.text()
        jsonData["summary"] = self.summary.toPlainText()
        jsonData["chapters"] = []
        for chapter in self.chapters:
            chapterData = {}
            jsonData["chapters"].append(chapterData)
            chapterData["title"] = chapter.title.text()
            chapterData["summary"] = chapter.summary.toPlainText()
            chapterData["scenes"] = []
            for scene in chapter.scenes:
                sceneData = {}
                chapterData["scenes"].append(sceneData)
                sceneData["summary"] = scene.summary.toPlainText()
                sceneData["text"] = scene.text.toPlainText()
        
        with open(filename + ".json", "w") as f:
            f.write(json.dumps(jsonData))

    def exportStory(self):
        filename = sanitize_filename(self.title.text())
        with open(filename + ".txt", "w") as f:
            f.write(self.title.text())
            f.write("\n\n")
            for chapter in self.chapters:
                f.write(chapter.title.text())
                f.write("\n")
                f.write("="*len(chapter.title.text()))
                f.write("\n\n")
                for scene in chapter.scenes:
                    f.write(scene.text.toPlainText())
                    f.write("\n\n")


# Create a Qt application
app = QApplication([])

# Create and show the form
form = StoryWriter()
form.show()

# Run the main Qt loop
app.exec_()
