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

# Create a Qt application
app = QApplication([])

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
        app.beep()
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

#Note to self: update Scene to have a root widget rather than adding things directly to its layout
class Scene(QWidget):
    def __init__(self, parentChapter, sceneData=None):
        super().__init__()
        self.parentChapter = parentChapter
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.parentChapter.scenesLayout.addWidget(self)

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
        self.text.setToolTip("""This is the finished output text for this story.""")

        self.textLayout.addWidget(QLabel("Text"),0,1)
        self.textLayout.addWidget(self.text,1,1)

        self.layout.addLayout(self.textLayout)
        
        buttons = QHBoxLayout()

        self.move_up = QPushButton("Move up")
        self.move_up.clicked.connect(self.moveSceneUp)
        buttons.addWidget(self.move_up)
        self.move_down = QPushButton("Move down")
        self.move_down.clicked.connect(self.moveSceneDown)
        buttons.addWidget(self.move_down)

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
        self.parentChapter.scenesLayout.removeWidget(self)
        self.parentChapter.parentStory.update()
        self.deleteLater()
        return

    def generateScene(self):
        chapter = self.parentChapter
        story = chapter.parentStory
        chapter_index = None
        scene_index = None
        for i in range(story.chapterLayout.count()):
            if story.chapterLayout.itemAt(i).widget() == chapter:
                chapter_index= i
                break
        for i in range(chapter.scenesLayout.count()):
            if chapter.scenesLayout.itemAt(i).widget() == self:
                scene_index = i
                break

        #print("chapter index " + str(chapter_index))
        #print("scene index " + str(scene_index))

        prompt = "{{[INPUT]}}\nYou are to take the role of an author writing a story. The story is titled \"" + story.title.text() + "\"."
        if len(story.summary.toPlainText()) > 0:
            prompt = prompt + "\n\nGeneral background information: " + story.summary.toPlainText()
        prompt = prompt + "\n\nThe story so far has had the following major events happen:"
        for c in range(chapter_index + 1):
            chapter = story.chapterLayout.itemAt(c).widget()
            prompt = prompt + "\n\n" + chapter.summary.toPlainText()
        prompt = prompt + "\n\nThe current chapter is titled \"" + chapter.title.text() + "\""
        if scene_index > 1:
            prompt = prompt + "\n\nThe following scenes have already happened in this chapter:"
            for s in range(scene_index-1):
                prompt = prompt + "\n" + chapter.scenesLayout.itemAt(s).widget().summary.toPlainText()
        if scene_index > 0:
            prompt = prompt +"\n\nThe most recent scene before this one was:\n\n" + chapter.scenesLayout.itemAt(scene_index-1).widget().text.toPlainText()

        prompt = prompt + "\n\nYou are now writing the next scene in which the following occurs: " + self.summary.toPlainText() \
                 + "\n\nPlease write out this scene.\n{{[OUTPUT]}}"

        print(prompt)
        self.text.setPlainText(getResult(prompt, None))
        return

    def moveScene(self, up):
        chapter = self.parentChapter
        scene_index = None
        scene_count = chapter.scenesLayout.count()
        for i in range(scene_count):
            if chapter.scenesLayout.itemAt(i).widget() == self:
                scene_index = i
                break
        target = scene_index
        if up:
            target = target - 1
        else:
            target = target + 1
        if target < 0 or target >= scene_count or scene_index < 0 or scene_index >= scene_count:
            return
        if scene_index > target:
            scene_index, target = target, scene_index
        layout = chapter.scenesLayout
        widget1 = layout.itemAt(scene_index).widget()
        widget2 = layout.itemAt(target).widget()
        layout.removeWidget(widget1)
        layout.removeWidget(widget2)
        layout.insertWidget(scene_index, widget2)
        layout.insertWidget(target, widget1)
        chapter.update()
        return    

    def moveSceneUp(self):
        self.moveScene(True)
    def moveSceneDown(self):
        self.moveScene(False)

class Chapter(QFrame):
    def __init__(self, parentStory, chapterData=None):
        super().__init__()
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.parentStory = parentStory
        
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

        self.scenesWidget = QWidget()
        self.scenesLayout = QVBoxLayout()
        self.scenesLayout.setContentsMargins(20,0,0,0)
        self.scenesWidget.setLayout(self.scenesLayout)
        
        self.layout.addWidget(self.scenesWidget)

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

        self.parentStory.chapterLayout.addWidget(self)
        #self.parentStory.chapterLayout.update()
        self.parentStory.scrollContent.adjustSize()

    def deleteChapter(self):
        parentLayout = self.parentStory.chapterLayout
        parentLayout.removeWidget(self)
        self.deleteLater()
        self.parentStory.update()

    def addScene(self):
        Scene(self)

    def generateSummary(self):
        chapter = self
        story = chapter.parentStory
        chapter_index = None
        for i in range(story.chapterLayout.count()):
            if story.chapterLayout.itemAt(i).widget() == chapter:
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
        scenesLayout = story.chapterLayout.itemAt(chapter_index).widget().scenesLayout
        for i in range(scenesLayout.count()):
            prompt = prompt + "\n\n" + scenesLayout.itemAt(i).widget().text.toPlainText()

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

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)

        self.scrollContent = QWidget(self.scrollArea)
        self.chapterLayout = QVBoxLayout(self.scrollContent)
        self.scrollContent.setLayout(self.chapterLayout)
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
        for widget in self.scrollContent.findChildren(QWidget):
            widget.deleteLater()
        self.chapterLayout.update()
        for chapterData in jsonData["chapters"]:
            Chapter(self, chapterData)

    def saveStory(self):
        filename = sanitize_filename(self.title.text())
        jsonData = {}
        jsonData["title"] = self.title.text()
        jsonData["summary"] = self.summary.toPlainText()
        jsonData["chapters"] = []
        for i in range(self.chapterLayout.count()):
            chapter = self.chapterLayout.itemAt(i).widget()
            chapterData = {}
            jsonData["chapters"].append(chapterData)
            chapterData["title"] = chapter.title.text()
            chapterData["summary"] = chapter.summary.toPlainText()
            chapterData["scenes"] = []
            for i in range(chapter.scenesLayout.count()):
                scene = chapter.scenesLayout.itemAt(i).widget()
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
            for i in range(self.chapterLayout.count()):
                chapter = self.chapterLayout.itemAt(i).widget()
                f.write(chapter.title.text())
                f.write("\n")
                f.write("="*len(chapter.title.text()))
                f.write("\n\n")
                for i in range(chapter.scenesLayout.count()):
                    scene = chapter.scenesLayout.itemAt(i).widget()
                    f.write(scene.text.toPlainText())
                    f.write("\n\n")

                

# Create and show the form
form = StoryWriter()
form.show()

# Run the main Qt loop
app.exec_()
