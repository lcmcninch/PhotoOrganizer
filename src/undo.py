""" Undo commands for Photo Organizer """
from PyQt4 import QtGui, QtCore
from datastore import FieldObject
from datetime import datetime
from ImageMan import getThumbnailIcon
import os
from PIL import Image
from shared import trashDir
import shutil


class newFieldCmd(QtGui.QUndoCommand):
    """ Undo command for inserting a new field into the album

    Arguments:
        main (PhotoOrganizer): The instance of the main app
        name (str, QString): The name of the new field
    """
    def __init__(self, main, name, parent=None):
        super(newFieldCmd, self).__init__(parent)
        self.main = main
        self.field = FieldObject(str(name), filt=True, tags=True)

    def redo(self):
        self.main.model.insertColumns(field=self.field)

    def undo(self):
        col = self.main.fields.index(self.field)
        self.main.model.removeColumns(col)


class removeRowCmd(QtGui.QUndoCommand):
    """ Undo command for removing a photo

    Arguments:
        main (PhotoOrganizer): The main application instance
        photo (Photo): The photo object to be deleted
    """

    description = "Delete Photo"

    def __init__(self, viewer, photo, parent=None):
        self.viewer = viewer
        self.main = viewer.main
        self.photo = photo
        self.index = viewer.imageList.index(photo)
        if self.main:
            self.row = self.main.album.index(photo)
        else:
            self.row = None
        description = self.description.replace('Photo', photo.fileName)
        super(removeRowCmd, self).__init__(description, parent)

    def redo(self):
        if self.main:
            # Remove the photo
            self.main.model.removeRows(self.row)

            # Select the next row
            newRow = self.row
            if len(self.main.album) <= self.row:
                newRow = len(self.main.album)
            self.main.view.setCurrentPhoto(newRow)

        # Move the file to the trash
        if os.path.exists(self.photo.filePath):
            trashTime = datetime.now().strftime('.%Y%m%d%H%M%S')
            self.trashFile = os.path.join(trashDir, self.photo.fileName + trashTime)
            shutil.move(self.photo.filePath, self.trashFile)
        else:
            self.trashFile = None

        # Update the viewer
        self.viewer.imageList.remove(self.photo)
        if len(self.viewer.imageList) == 0:
            self.viewer.close()
            return
        index = self.index
        if index >= len(self.viewer.imageList):
            index = len(self.viewer.imageList) - 1
        self.viewer.setImage(index)

    def undo(self):
        if self.main:
            # Re-insert the photo
            self.main.model.insertRows(self.photo, self.row)

            # Select our row
            self.main.view.setCurrentPhoto(self.row)

        # Restore the file from the trash
        if self.trashFile is not None:
            shutil.move(self.trashFile, self.photo.filePath)

        # Update the viewer
        self.viewer.imageList.insert(self.index, self.photo)
        self.viewer.setImage(self.index)
        if self.viewer.isHidden():
            self.viewer.show()


class imageRotateCmd(QtGui.QUndoCommand):
    """ Undo command for rotating a photo

    The file is saved to .trash for undo/redo purposes

    Arguments:
        main (PhotoOrganizer): The main application instance
        photo (Photo): The photo object to be deleted
        angle (int): The angle to rotate the photo
    """

    description = "Rotate"

    def __init__(self, viewer, photo, angle, parent=None):
        self.viewer = viewer
        self.main = viewer.main
        self.photo = photo
        self.angle = angle

        description = '{} {}: {}'.format(self.description, photo.fileName,
                                         angle)
        super(imageRotateCmd, self).__init__(description, parent)

    def redo(self):
        self.do(self.angle)

    def undo(self):
        self.do(-self.angle)

    def do(self, angle):
        # Do the rotation
        im = Image.open(self.photo.filePath)
        exif = im.info['exif']
        im = im.rotate(angle, expand=True)
        im.save(self.photo.filePath, exif=exif)
        im.close()
        self.viewer.setImage(self.photo)

        # Set the thumbnail
        if self.main:
            thumb = getThumbnailIcon(self.photo.filePath)
            row = self.main.album.index(self.photo)
            index = self.main.model.index(row, 0)
            self.main.model._setData(index, thumb, QtCore.Qt.DecorationRole)
