from PySide6.QtWidgets import QLayout, QSizePolicy
from PySide6.QtCore import Qt, QRect, QSize, QPoint


class FlowLayout(QLayout):
    """
    A robust custom layout that wraps its child widgets to the next line 
    when horizontal space is exhausted, acting like CSS flex-wrap: wrap.
    """
    def __init__(self, parent=None, margin=0, spacing=20):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effective_rect = rect.adjusted(left, top, -right, -bottom)
        x = effective_rect.x()
        y = effective_rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.itemList:
            wid = item.widget()
            if wid and not wid.isVisible():
                continue

            item_w = item.sizeHint().width()
            item_h = item.sizeHint().height()

            # If adding this widget exceeds the container width, wrap to next line
            if x + item_w > effective_rect.right() and lineHeight > 0:
                x = effective_rect.x()
                y = y + lineHeight + spacing
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), QSize(item_w, item_h)))

            x = x + item_w + spacing
            lineHeight = max(lineHeight, item_h)

        return y + lineHeight - rect.y() + bottom
