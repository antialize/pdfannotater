import popplerqt4
import sys
from PyQt4 import QtGui, QtCore, uic
import math
import os
import subprocess


class GeometryCommand(QtGui.QUndoCommand):
    def __init__(self, item, f, t, text):
        QtGui.QUndoCommand.__init__(self, text)
        self.item = item
        self.f = f
        self.t = t

    def undo(self):
        self.item.changeRect(self.f)

    def redo(self):
        self.item.changeRect(self.t)


class PdfPageItem(QtGui.QGraphicsItem):
    def __init__(self, page):
        QtGui.QGraphicsItem.__init__(self)
        self.image = None
        self.cachedRect = None
        self.page = page
        tmp = page.renderToImage(75, 75)
        self.rect = QtCore.QRectF(0, 0, tmp.width(), tmp.height())
        self.setFlag(QtGui.QGraphicsItem.ItemUsesExtendedStyleOption, True)


    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        d = option.levelOfDetailFromTransform(painter.worldTransform())
        d = min(d, 8)
        r = self.boundingRect()
        top = math.floor(r.top()*d)
        left = math.floor(r.left()*d)
        bottom = math.ceil(r.bottom()*d)
        right = math.ceil(r.right()*d)

        if (top,left,right,bottom) != self.cachedRect:
            self.image = self.page.renderToImage(
                75*d, 75*d, left, top, right-left, bottom-top)
            self.cachedRect = (top,left,right,bottom)
        painter.drawImage(
            QtCore.QRectF(left/d, top/d, (right-left)/d, (bottom-top)/d),
            self.image)

class PropertiesModel(QtCore.QAbstractTableModel):
    def __init__(self, item):
        QtCore.QAbstractItemModel.__init__(self)
        self.item = item

    def columnCount(self, parent):
        return 2

    def rowCount(self, parent):
        return len(self.item.properties)

    def data(self, index, role):
        if not index.isValid():
            return None
        return "HAT"


class ItemBase(QtGui.QGraphicsItem):
    def __init__(self, page):
        QtGui.QGraphicsItem.__init__(self)
        self.page = page
        self.startRect = None
        self.isHovering = False
        self.setAcceptHoverEvents(True)
        self.resizeTop = False
        self.resizeBottom = False
        self.resizeLeft = False
        self.resizeRight = False
        self.moveStart = None
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.properties = ['width', 'height', 'top', 'left']

    def boundingRect(self):
        r = QtCore.QRectF(self.innerRect)
        r.setLeft(r.left()-2)
        r.setTop(r.top()-2)
        r.setRight(r.right()+2)
        r.setBottom(r.bottom()+2)
        return r

    def changeRect(self, r):
        self.prepareGeometryChange()
        self.innerRect = rect

    def paint(self, painter, option, widget):
        if self.isHovering or self.isSelected():
            if self.isSelected():
                pen = QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.SolidLine)
            else:
                pen = QtGui.QPen(QtCore.Qt.black, 0, QtCore.Qt.DotLine)

            # painter.setCompositionMode(QtGui.QPainter.RasterOp_SourceXorDestination)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.NoBrush)
            r = QtCore.QRectF(self.innerRect)
            r.setLeft(r.left()-1)
            r.setTop(r.top()-1)
            r.setRight(r.right()+1)
            r.setBottom(r.bottom()+1)
            painter.drawRect(self.boundingRect())

    def onLeft(self, pos):
        return pos.x() <= self.innerRect.left() + 3

    def onRight(self, pos):
        return pos.x() >= self.innerRect.right() - 3

    def onTop(self, pos):
        return pos.y() <= self.innerRect.top() + 3

    def onBottom(self, pos):
        return pos.y() >= self.innerRect.bottom() - 3

    def mousePressEvent(self, event):
        p = event.pos()
        self.resizeTop = self.resizeBottom = False
        self.resizeLeft = self.resizeRight = False
        self.moveStart = None
        self.startRect = QtCore.QRectF(self.innerRect)
        self.myEvent = False
        if event.button() == QtCore.Qt.LeftButton:
            # self.page.select(self)
            if event.modifiers() != QtCore.Qt.ControlModifier:
                self.resizeTop = self.onTop(p)
                self.resizeBottom = self.onBottom(p)
                self.resizeLeft = self.onLeft(p)
                self.resizeRight = self.onRight(p)

            if (not self.resizeTop and not self.resizeBottom
                    and not self.resizeLeft and not self.resizeRight):
                if event.modifiers() == QtCore.Qt.ControlModifier:
                    self.moveStart = (self.innerRect.topLeft(), p)
                    self.myEvent = True
                else:
                    QtGui.QGraphicsItem.mousePressEvent(self, event)
            else:
                self.myEvent = True
        else:
            QtGui.QGraphicsItem.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        if self.myEvent:
            p = event.pos()
            self.prepareGeometryChange()
            if self.resizeTop:
                self.innerRect.setTop(p.y())
            if self.resizeBottom:
                self.innerRect.setBottom(p.y())
            if self.resizeLeft:
                self.innerRect.setLeft(p.x())
            if self.resizeRight:
                self.innerRect.setRight(p.x())
            self.commandName = "Resize item"
            if self.moveStart:
                self.innerRect.moveTo(
                    self.moveStart[0].x() + p.x() - self.moveStart[1].x(),
                    self.moveStart[0].y() + p.y() - self.moveStart[1].y())
                self.commandName = "Move item"
        else:
            QtGui.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.myEvent:
            if self.innerRect != self.startRect:
                GeometryCommand(
                    self, self.startRect,
                    QtCore.QRectF(self.innerRect), self.commandName)
        else:
            QtGui.QGraphicsItem.mouseReleaseEvent(self, event)

    def hoverEnterEvent(self, event):
        self.isHovering = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.isHovering = False
        self.update()

    def hoverMoveEvent(self, event):
        p = event.pos()
        if self.onLeft(p) and self.onTop(p):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.onRight(p) and self.onBottom(p):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.onRight(p) and self.onTop(p):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        elif self.onLeft(p) and self.onBottom(p):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        elif self.onLeft(p) or self.onRight(p):
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif self.onTop(p) or self.onBottom(p):
            self.setCursor(QtCore.Qt.SizeVerCursor)
        else:
            self.setCursor(QtCore.Qt.OpenHandCursor)


class ImageItem(ItemBase):
    def __init__(self, page):
        ItemBase.__init__(self, page)
        self.image = QtGui.QImage("/home/jakobt/tux2.png")
        self.innerRect = QtCore.QRectF(
            100, 100, self.image.width(), self.image.height())

    def paint(self, painter, option, widget):
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        painter.drawImage(self.innerRect, self.image,
                          QtCore.QRectF(
                              0, 0, self.image.width(), self.image.height()))
        ItemBase.paint(self, painter, option, widget)

    def getName(self):
        return "Image"

    def save(self, s):
        s << self.image
        s << self.innerRect

    @staticmethod
    def id():
        return 1


class RectItem(ItemBase):
    def __init__(self, page):
        ItemBase.__init__(self, page)
        self.innerRect = QtCore.QRectF(0, 0, 100, 100)
        self.pen = QtGui.QPen(QtCore.Qt.black, 2)
        self.brush = QtCore.Qt.blue

    def paint(self, painter, option, widget):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawRect(self.innerRect)
        ItemBase.paint(self, painter, option, widget)

    def getName(self):
        return "Rect"

    def save(self, stream):
        stream << self.innerRect

    @staticmethod
    def id():
        return 2


class TextItem(QtGui.QGraphicsTextItem):
    def __init__(self, page, font=None):
        QtGui.QGraphicsTextItem.__init__(self)
        self.page = page
        # self.isHovering=False
        # self.setAcceptHoverEvents(True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtGui.QGraphicsItem.ItemIsSelectable, True)
        self.setDefaultTextColor(QtCore.Qt.red)
        document = QtGui.QTextDocument()
        document.setDocumentMargin(0)
        self.setDocument(document)
        self.setPlainText("Hello")
        if font:
            self.setFont(font)
        # self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)

    def save(self, s):
        s << self.toHtml()
        s << self.pos()

    def load(self, s):
        html = QtCore.QString()
        s >> html
        pos = QtCore.QPointF()
        s >> pos
        self.setPos(pos)
        self.setHtml(html)

    def getName(self):
        return "Text"

    @staticmethod
    def id():
        return 3

    def selectAll(self):
        c = self.textCursor()
        c.beginEditBlock()
        c.select(QtGui.QTextCursor.Document)
        c.insertHtml("Boo")
        setTextCursor(c)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        c = self.textCursor()
        c.clearSelection()
        self.setTextCursor(c)
        QtGui.QGraphicsTextItem.focusOutEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        if self.textInteractionFlags() == QtCore.Qt.NoTextInteraction:
            self.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        QtGui.QGraphicsTextItem.mouseDoubleClickEvent(self, event)


class ObjectTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, project):
        QtCore.QAbstractItemModel.__init__(self)
        self.project = project

    def columnCount(self, parent):
        return 1

    def rowCount(self, parent):
        p = self.project
        if parent.isValid():
            p = parent.internalPointer()
        if isinstance(p, Project):
            return len(p.pages)
        elif isinstance(p, Page):
            return len(p.objects)
        else:
            return 0

    def data(self, index, role):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        i = index.internalPointer()
        if isinstance(i, Page):
            return "Page %i" % (i.number + 1)
        elif isinstance(i, ItemBase):
            return i.getName()
        return None

    def parent(self, index):
        if not index.isValid():
            return None
        p = index.internalPointer()
        if isinstance(p, Page):
            return self.createIndex(0, 0, p.project)
        elif isinstance(p, ItemBase):
            return self.createIndex(0, 0, p.page)
        return QtCore.QModelIndex()

    def index(self, row, column, parent):
        p = self.project
        if parent.isValid():
            p = parent.internalPointer()
        if row < 0:
            return None
        if isinstance(p, Project):
            if row >= len(p.pages):
                return None
            return self.createIndex(row, column, p.pages[row])
        elif isinstance(p, Page):
            if row >= len(p.objects):
                return None
            return self.createIndex(row, column, p.objects[row])
        else:
            return None


class Page(QtCore.QObject):
    def __init__(self, project, i):
        QtCore.QObject.__init__(self)
        self.number = i
        self.objects = []

        self.scene = QtGui.QGraphicsScene()
        self.scene.setBackgroundBrush(QtCore.Qt.gray)
        self.pageItem = PdfPageItem(project.document.page(i))
        self.scene.addItem(self.pageItem)

        self.project = project
        self.selectedItem = None

    def addText(self):
        text = TextItem(self, self.myFont)
        font_metrics = QtGui.QFontMetrics(text.font())
        pos = a.view.mapToScene(a.view.mapFromGlobal(QtGui.QCursor.pos()))
        text.setPos(
            pos.x(),
            pos.y() - font_metrics.ascent() - font_metrics.leading() - 1)
        self.scene.addItem(text)
        self.objects.append(text)
        text.setSelected(True)
        text.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
        selection = text.textCursor()
        selection.select(QtGui.QTextCursor.Document)
        text.setTextCursor(selection)
        text.setFocus()

    def save(self, stream):
        stream.writeUInt32(len(self.objects))
        for obj in self.objects:
            stream.writeUInt32(obj.id())
            obj.save(stream)

    def load(self, stream):
        count = stream.readUInt32()
        for i in range(count):
            d = stream.readUInt32()
            for t in [ImageItem, RectItem, TextItem]:
                if t.id() != d:
                    continue
                item = t(self)
                item.load(stream)
                self.scene.addItem(item)
                self.objects.append(item)

    def deleteSelection(self):
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
            self.objects.remove(item)

    def itemSelected(self, item):
        self.parent.itemSelected.emit(item)

    def changeFont(self, font):
        self.myFont = font
        for item in self.scene.selectedItems():
            if isinstance(item, TextItem):
                item.setFont(font)


class Project(QtCore.QObject):
    itemSelected = QtCore.pyqtSignal([QtGui.QGraphicsItem])

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.undoStack = QtGui.QUndoStack()
        self.document = None
        self.pages = []
        self.treeModel = ObjectTreeModel(self)
        self.path = None

    def __loadPdf__(self, pdfData):
        self.undoStack.clear()
        self.pdfData = pdfData
        self.document = popplerqt4.Poppler.Document.loadFromData(pdfData)
        self.document.setRenderHint(
            popplerqt4.Poppler.Document.Antialiasing, True)
        self.document.setRenderHint(
            popplerqt4.Poppler.Document.TextAntialiasing, True)
        self.pages = [Page(self, i) for i in range(self.document.numPages())]

    def create(self, path):
        pdf = QtCore.QFile(path)
        pdf.open(QtCore.QIODevice.ReadOnly)
        pdfData = pdf.readAll()
        self.__loadPdf__(pdfData)
        self.path = QtCore.QString(os.path.splitext(str(path))[0]+".pep")

    def save(self):
        f = QtCore.QFile(self.path)
        f.open(QtCore.QIODevice.WriteOnly)
        stream = QtCore.QDataStream(f)
        stream.writeUInt32(0x2a04c304)
        stream.writeUInt32(0)
        stream << QtCore.QString(self.path)
        stream << self.pdfData
        stream.writeUInt32(len(self.pages))
        for page in self.pages:
            page.save(stream)

    def saveas(self, path):
        self.path = QtCore.QString(path)
        self.save()

    def load(self, path):
        f = QtCore.QFile(path)
        f.open(QtCore.QIODevice.ReadOnly)
        stream = QtCore.QDataStream(f)
        if stream.readUInt32() != 0x2a04c304:
            return None
        version = stream.readUInt32()
        if version > 0:
            return None
        self.path = QtCore.QString()
        stream >> self.path
        pdfData = QtCore.QByteArray()
        stream >> pdfData
        self.__loadPdf__(pdfData)
        pages = stream.readUInt32()
        for i in range(pages-len(self.pages)):
            self.addPage()
        for page in self.pages:
            page.load(stream)
        self.changeFont(self.font)

    def addPage():
        pass

    def export(self, path):
        printer = QtGui.QPrinter()
        printer.setColorMode(QtGui.QPrinter.Color)
        printer.setOutputFormat(QtGui.QPrinter.PdfFormat)
        printer.setOutputFileName(path+"~1")
        printer.setPageMargins(0, 0, 0, 0, QtGui.QPrinter.Point)
        page = self.document.page(0)
        printer.setPaperSize(page.pageSizeF(), QtGui.QPrinter.Point)

        painter = QtGui.QPainter()
        if not painter.begin(printer):
            return

        first = True
        for page in self.pages:
            if first:
                first = False
            else:
                printer.newPage()
            page.pageItem.hide()
            bg = page.scene.backgroundBrush()
            page.scene.setBackgroundBrush(QtGui.QBrush(QtCore.Qt.NoBrush))
            page.scene.render(
                painter, QtCore.QRectF(), page.pageItem.boundingRect())
            page.scene.setBackgroundBrush(bg)
            page.pageItem.show()
        painter.end()
        del painter
        del printer
        f = QtCore.QFile(path+"~2")
        f.open(QtCore.QIODevice.WriteOnly)
        f.write(self.pdfData)
        f.close()
        subprocess.call(
            ["pdftk", path+"~1",
             "multibackground", path+"~2",
             "output", path])
        os.remove(path+"~1")
        os.remove(path+"~2")

    def changeFont(self, font):
        self.font = font
        for page in self.pages:
            page.changeFont(font)


class MainWindow(QtGui.QMainWindow):
    currentPageChanged = QtCore.pyqtSignal(Page)

    def setCurrentPage(self, page):
        if page == self.currentPage:
            return
        self.currentPage = page
        self.currentPageChanged.emit(page)
        self.treeView.clearSelection()
        if page:
            self.treeView.selectionModel().setCurrentIndex(
                self.project.treeModel.createIndex(0, 0, page),
                QtGui.QItemSelectionModel.ClearAndSelect)

    def getCurrentPage(self):
        return self.currentPage

    def currentObjectChanged(self, current, previous):
        p = current.internalPointer()
        if isinstance(p, Page):
            self.setCurrentPage(p)
        elif isinstance(p, ItemBase):
            self.setCurrentPage(p.page)

    def __init__(self):
        QtCore.QObject.__init__(self)
        uic.loadUi(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         "main.ui"),
            self)

        self.fontCombo = QtGui.QFontComboBox()
        self.textToolBar.addWidget(self.fontCombo)
        self.fontCombo.currentFontChanged.connect(self.handleFontChange)

        self.fontSizeCombo = QtGui.QComboBox()
        for i in range(8, 30, 2):
            self.fontSizeCombo.addItem(QtCore.QString("%d" % i))
        v = QtGui.QIntValidator(2, 64, self)
        self.fontSizeCombo.setValidator(v)
        self.textToolBar.addWidget(self.fontSizeCombo)
        self.fontSizeCombo.currentIndexChanged.connect(self.handleFontChange)

        # fontColorToolButton = new QToolButton;
        # fontColorToolButton->setPopupMode(QToolButton::MenuButtonPopup);
        # fontColorToolButton->setMenu(createColorMenu(SLOT(textColorChanged()),
        #                                              Qt::black));
        # textAction = fontColorToolButton->menu()->defaultAction();
        # fontColorToolButton->setIcon(createColorToolButtonIcon(
        # ":/images/textpointer.png", Qt::black));
        # fontColorToolButton->setAutoFillBackground(true);
        # connect(fontColorToolButton, SIGNAL(clicked()),
        #         this, SLOT(textButtonTriggered()));

        project = Project()
        # view = PageView(None, main)
        self.currentPage = None

        # self.actionAddImage.triggered.connect(self.addImage)
        self.actionAddText.triggered.connect(self.addText)

        project.itemSelected.connect(self.itemSelected)

        toolGroup = QtGui.QActionGroup(self)
        toolGroup.addAction(self.actionSizeTool)
        toolGroup.addAction(self.actionRectangleTool)
        toolGroup.addAction(self.actionLineTool)
        toolGroup.addAction(self.actionTextTool)
        self.actionSizeTool.setChecked(True)

        self.treeView.setModel(project.treeModel)
        self.treeView.selectionModel().currentChanged.connect(
            self.currentObjectChanged)

        self.currentPageChanged.connect(self.view.currentPageChanged)

        self.project = project

        self.handleFontChange()

    def doNewProject(self, path):
        self.setCurrentPage(None)
        self.project.create(path)
        if self.project.pages:
            self.setCurrentPage(self.project.pages[0])
        self.handleFontChange()

    def newProject(self):
        path = QtGui.QFileDialog.getOpenFileName(
            self, "Open PDF file", "", "PDF document (*.pdf);;All files (*)")
        if path:
            self.doNewProject(path)

    def export(self):
        a, e = os.path.splitext(str(self.project.path))
        path = a+"_ann.pdf"
        # path = QtGui.QFileDialog.getSaveFileName(
        #     self, "Export pdf", "", "Pdf Documents (*.pdf);;All files (*)")
        if path:
            self.project.export(path)

    def saveas(self):
        path = QtGui.QFileDialog.getSaveFileName(
            self, "Save Project",
            self.project.path if self.project.path else "",
            "Pro Documents (*.pro);;All files (*)")
        if path:
            self.project.saveas(path)

    def doLoad(self, path):
        self.setCurrentPage(None)
        self.project.load(path)
        if self.project.pages:
            self.setCurrentPage(self.project.pages[0])

    def load(self):
        path = QtGui.QFileDialog.getOpenFileName(
            self, "Open Project",
            self.project.path if self.project.path else "",
            "Pro Documents (*.pro);;All files (*)")
        if path:
            self.doLoad(path)

    def save(self):
        if not self.project.path:
            self.saveas()
        else:
            self.project.save()

    def addImage(self):
        path = QtGui.QFileDialog.getOpenFileName(
            self, "Add image", "",
            "Image Formats (*.bmp *.jgp *.jpeg *.mng *.png *.pbm *.ppm "
            "*.tiff);;All files(*)")
        if path:
            pass

    def addText(self):
        self.currentPage.addText()

    def deleteSelection(self):
        self.currentPage.deleteSelection()

    def exportSaveAndQuit(self):
        self.save()
        self.export()
        self.close()

    def handleFontChange(self, *_):
        font = self.fontCombo.currentFont()
        font.setPointSize(self.fontSizeCombo.currentText().toInt()[0])
        font.setWeight(QtGui.QFont.Bold
                       if self.actionBold.isChecked()
                       else QtGui.QFont.Normal)
        font.setItalic(self.actionItalic.isChecked())
        font.setUnderline(self.actionUnderline.isChecked())
        self.project.changeFont(font)

    def itemSelected(item):
        font = item.font()
        color = item.defaultTextColor()
        self.fontCombo.setCurrentFont(font)
        self.fontSizeCombo.setEditText(
            QtCore.QString().setNum(font.pointSize()))
        self.boldAction.setChecked(font.weight() == QtGui.QFont.Bold)
        self.italicAction.setChecked(font.italic())
        self.underlineAction.setChecked(font.underline())


def main():
    global a
    app = QtGui.QApplication(sys.argv)

    a = MainWindow()
    a.show()
    if len(app.arguments()) > 1:
        pep = os.path.splitext(str(app.arguments()[1]))[0]+".pep"
        if os.path.exists(pep):
            a.doLoad(pep)
        else:
            a.doNewProject(app.arguments()[1])
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
