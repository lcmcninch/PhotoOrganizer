from PyQt4 import QtCore, QtGui
from datetime import datetime

# Place holder
edit_role = QtCore.Qt.EditRole
model_idx = QtCore.QModelIndex


class AlbumModel(QtCore.QAbstractTableModel):

    """
    Model who's dataset is a TabularFieldEntryList
    """

    dirty = QtCore.pyqtSignal()

    def __init__(self, dataset, parent=None):
        """ Initialize Model """
        super(AlbumModel, self).__init__(parent)
        self.dataset = dataset
        self.undoStack = QtGui.QUndoStack()

    def columnCount(self, index=model_idx()):
        """ Model required function that returns the number of columns """
        return len(self.dataset.fields)

    def rowCount(self, index=model_idx()):
        """ Model required function that returns the number of rows """
        return len(self.dataset)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """ Model required function that returns data for a given index """
        if (role == QtCore.Qt.DisplayRole) or (role == QtCore.Qt.EditRole):
            k = self.dataset[index.row(), self.dataset.fields[index.column()]]
            return QtCore.QVariant(k)
#         elif role == QtCore.Qt.BackgroundRole:
#             if self.dataset[index.row()].scrapped:
#                 return QtCore.QVariant(QtGui.QColor(255, 0, 0, 123))
        elif role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                photo = self.dataset[index.row()]
                return photo.thumb
        elif role == QtCore.Qt.TextAlignmentRole:
            return (QtCore.Qt.AlignCenter)
        else:
            return QtCore.QVariant()

    def insertColumns(self, position=None, columns=0,
                      index=QtCore.QModelIndex(), name=None, copyof=None):
        """ Model required function for inserting columns """
        if (position is None) or (position == -1):
            position = self.columnCount()
        self.beginInsertColumns(index, position, position + columns)
        self.dataset.insertField(position, name, copyof=copyof)
        self.endInsertColumns()
        self.dirty.emit()
        return True

    def removeColumns(self, position, columns=0, index=model_idx(),
                      force=False):
        """ Model Function for removing columns

        If the field is required this method will return a false but not
        cause and error. If the force argument is given as True the specified
        field will be deleted no matter its required status.

        """
        field = self.dataset.fields[position]
        if field.required and (not force):
            return False
        else:
            self.beginRemoveColumns(index, position, position + columns)
            self.dataset.removeField(position, force)
            self.endRemoveColumns()
            self.dirty.emit()
            return True

    def removeField(self, field, force=False):
        """  Allows for removing of columns by name """
        idx = self.dataset.field_names.index(field)
        result = self.removeColumns(idx, force=force)
        return result

    def insertRows(self, position=None, rows=0, entry=None, uuid=''):
        """ Model required function for inserting rows """
        if position is None:
            position = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows)
        if entry:
            self.dataset.insert(position, entry)
        else:
            self.dataset.addEntry(uuid=uuid)
        self.endInsertRows()
        self.dirty.emit()
        return True

    def removeRows(self, position, rows=0, index=model_idx()):
        """ Model required function for removing rows """
        self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows)
        self.dataset.removeEntry(position)
        self.endRemoveRows()
        self.dirty.emit()
        return True

    def deleteCells(self, indexes):
        """ Custom function to delete the values from cells """
        command = deleteCmd(self, indexes)
        self.undoStack.push(command)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """ Model required function that sets data changes passed to model """
        row = index.row()
        field = self.headerData(index.column(), QtCore.Qt.Horizontal, 0)
        if field and index.isValid():
            field = self.dataset.fields[index.column()]
            if field.editor == field.CheckBoxEditor:
                cvalue = value.toBool()
            elif field.editor == field.DateEditEditor:
                if value.type() in (value.Date, value.DateTime):
                    cvalue = str(value.toPyObject().toString('yyyy-MM-dd'))
                else:
                    # Throw out any value that doesn't match the format
                    try:
                        cvalue = str(value.toString())
                        datetime.strptime(cvalue, '%Y-%m-%d')
                    except ValueError:
                        cvalue = ''
            else:
                cvalue = str(value.toString())
            if self.dataset[row, field] != cvalue:
                self.dirty.emit()
            self.dataset[row, field] = cvalue
            self.dataChanged.emit(index, index)
            return True
        else:
            return False

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Model required function that returns header data information """
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.FontRole:
                font = QtGui.QFont()
                font.setBold(self.dataset.fields[section].required)
                return QtCore.QVariant(font)
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self.dataset.field_names[section])
            if role == QtCore.Qt.BackgroundRole:
                return QtCore.QVariant(QtGui.QColor(255, 0, 0))
        else:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(int(section + 1))
        return QtCore.QVariant()

    def getHeaders(self, orientation):
        """ Return a list of the header strings for the give orientation """
        if orientation is QtCore.Qt.Horizontal:
            vec = xrange(self.columnCount())
        elif orientation is QtCore.Qt.Vertical:
            vec = xrange(self.rowCount())
        return [str(self.headerData(k, orientation).toString()) for k in vec]

    def flags(self, index):
        """ Model function to set item flags """
        fieldobj = self.dataset.fields[index.column()]
        if not index.isValid():
            return QtCore.Qt.ItemEnabled
        if fieldobj.editable:
            return QtCore.Qt.ItemFlags(
                QtCore.QAbstractTableModel.flags(self, index) |
                QtCore.Qt.ItemIsEditable)
        else:
            return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable |
                                       QtCore.Qt.ItemIsEnabled)

    def changeDataSet(self, dataset):
        """ Function that changes models underlying dataset

        This function is to facilitate changing the dataset for the model
        to be used in cases such as loading a file.

        """
        self.beginResetModel()
        self.dataset = dataset
        self.endResetModel()
        self.dirty.emit()


class AlbumSortFilterModel(QtGui.QSortFilterProxyModel):
    """ A proxy model subclass for filtering on any column """

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """ Re-implemented to apply the regular expression filter to all
        columns. If any column has a match, the row is accepted.

        Arguments:
            sourceRow (int): The row in question
            sourceParent (QModelIndex): The index of the row's parent.
        """
        sourceModel = self.sourceModel()
        for c in range(sourceModel.columnCount()):
            index = sourceModel.index(sourceRow, c, sourceParent)
            if index.data().toString().contains(self.filterRegExp()):
                return True
        return False


class deleteCmd(QtGui.QUndoCommand):

    description = "Delete Cells"

    def __init__(self, model, indexes, parent=None):
        self.indexes = indexes
        self.model = model
        self.old_values = [dex.data() for dex in self.indexes]
        super(deleteCmd, self).__init__(self.description, parent)

    def redo(self):
        # Delete the cells
        for cell in self.indexes:
            self.model.setData(cell, QtCore.QVariant(''))

    def undo(self):
        # Re-populate the cells
        for cell, val in zip(self.indexes, self.old_values):
            self.model.setData(cell, val)


if __name__ == "__main__":
    'print(__version__)'