from PyQt4 import QtGui, QtCore

class PageView(QtGui.QGraphicsView):
    zoomChanged = QtCore.pyqtSignal()
    pageChanged = QtCore.pyqtSignal()

    def __init__(self, parent):
        QtGui.QGraphicsView.__init__(self, parent)
        self.zoom = 1

    def updateTransform(self):
        t = QtGui.QTransform()
        t.scale(self.zoom, self.zoom)
        self.setTransform(t)
        self.zoomChanged.emit()

    def zoomReset(self):
        self.zoom = 1
        self.updateTransform()

    def zoomIn(self):
        self.zoom *= 1.5;
        self.updateTransform()

    def zoomOut(self):
        self.zoom /= 1.5;
        self.updateTransform()

    def wheelEvent(self, event):
        if event.modifiers() == QtCore.Qt.ControlModifier:
            self.zoom *= 2.0 ** (event.delta() / 300.0)
            self.updateTransform()
        else:
            QtGui.QGraphicsView.wheelEvent(self, event)

    def currentPageChanged(self, page):
        self.currentPage = page
        self.setScene(page.scene if page else None)
        self.pageChanged.emit()
