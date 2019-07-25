from __future__ import division
from tkinter import Frame, Canvas, TRUE, FALSE, BOTH, Tk
import tkinter.messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
from tkinter.messagebox import showerror
import os
import glob
import random
from os.path import exists, join, isdir

COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
CLICKED = True
RADIUS = 5
TOP_LEFT = 0
BOTTOM_RIGHT = 1
EDIT = 'edit'
CREATE = 'create'

class LabelCanvas():
    def __init__(self, master, bg='purple', r=5):
        self.parent = master
        self.parent.title("LabelTool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=TRUE)
        self.parent.resizable(width = TRUE, height = TRUE)
        self.r = r

        self._init_mouse_state()
        self._create_canvas(bg)
        self._init_vars()

    def _init_mouse_state(self):
        self.STATE = {}
        self.STATE['clicked'] = not CLICKED
        self.STATE['action'] = CREATE
        self.STATE['x'], self.STATE['y'] = 0, 0

    def _create_canvas(self, bg):
        self.canvas = Canvas(self.frame, cursor='tcross', bg=bg)
        self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<Button-1>", self._on_mouse_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.parent.bind("<Escape>", self._on_cancel_bbox)

    def _init_vars(self):
        self.bboxes_ids = []        # id references to bboxes managed by Tkinter        
        self.bboxes = []            # (x1,y1,x2,y2) for all ids in bboxes_ids
        self.curr_bbox_id = None    # current bbox being drawn
        self.corner_selected = -1   # flag bounding box corner selected or not
        self.corner_pos = None      # indicate TOP_LEFT or BOTTOM_RIGHT handle
        self.handlers = {}          # references to the circles in the rectangle corners

        self.hl = None              # horizontal line (not used now)
        self.vl = None
        self.tkimg = None

    def _add_bbox(self, event):
        if self.STATE['action'] == CREATE:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
        else:
            if self.corner_pos == BOTTOM_RIGHT:
                x, y = self.bboxes[self.corner_selected][2], self.bboxes[self.corner_selected][3]
            else:
                x, y = self.bboxes[self.corner_selected][0], self.bboxes[self.corner_selected][1]
            x1, x2 = min(x, event.x), max(x, event.x)
            y1, y2 = min(y, event.y), max(y, event.y)
        tmp_id = self.curr_bbox_id

        id_tl = self.canvas.create_oval(x1 - self.r, y1 - self.r, x1 + self.r, y1 + self.r, fill='black')
        id_br = self.canvas.create_oval(x2 - self.r, y2 - self.r, x2 + self.r, y2 + self.r, fill='yellow')
        self.handlers[self.curr_bbox_id] = [id_tl, id_br]

        self.bboxes.append((x1, y1, x2, y2))
        self.bboxes_ids.append(self.curr_bbox_id)
        self.curr_bbox_id = None

        return x1, y1, x2, y2, tmp_id

    def _del_bbox(self, bbox_id):
        self.canvas.delete(bbox_id)
        for c_id in self.handlers[bbox_id]:
            self.canvas.delete(c_id)
        
        idx = self.bboxes_ids.index(bbox_id)
        del self.handlers[bbox_id]
        del self.bboxes_ids[idx]
        del self.bboxes[idx]

    def _on_mouse_click_create(self, event):
        if not self.STATE['clicked']:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
            self.corner_selected, self.corner_pos = self._on_corner_selected(event.x, event.y, self.r)
            print(self.corner_pos)
            if self.corner_selected != -1:
                self.STATE['action'] = EDIT
        else:
            self._add_bbox(event)
    
    def _on_mouse_click_edit(self, event):
        # always performed on clicked so reset to CREATE afterwards
        self._add_bbox(event)
        self._del_bbox(self.bboxes_ids[self.corner_selected])
        self.STATE['action'] = CREATE
        self.corner_selected = -1

    def _on_mouse_click(self, event):
        if self.STATE['action'] == CREATE:
            self._on_mouse_click_create(event)
        else:
            self._on_mouse_click_edit(event)
        self.STATE['clicked'] = not self.STATE['clicked']
    
    def _on_mouse_move(self, event):
        if self.STATE['clicked']:
            if self.curr_bbox_id:
                self.canvas.delete(self.curr_bbox_id)
            self.curr_bbox_id = self.canvas.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[len(self.bboxes) % len(COLORS)])
        if self.corner_selected != -1:
            old_bbox = self.bboxes[self.corner_selected]
            self.canvas.delete(self.curr_bbox_id)
            if self.corner_pos == TOP_LEFT:
                x1, y1 = event.x, event.y
                x2, y2 = old_bbox[0], old_bbox[1]
            else:
                x1, y1 = event.x, event.y
                x2, y2 = old_bbox[2], old_bbox[3]
            outline = COLORS[len(self.bboxes) % len(COLORS)]
            self.curr_bbox_id = self.canvas.create_rectangle(x1, y1, x2, y2, width = 2, outline = outline)

    def _on_corner_selected(self, x, y, r):
        for idx, bbox in enumerate(self.bboxes):
            if self._is_vertex_inside_area(x, y, bbox[0], bbox[1], r):
                self.STATE['x'] = bbox[0]
                self.STATE['y'] = bbox[1]
                return idx, TOP_LEFT
            if self._is_vertex_inside_area(x, y, bbox[2], bbox[3], r):
                self.STATE['x'] = bbox[0]
                self.STATE['y'] = bbox[1]
                return idx, BOTTOM_RIGHT
        return -1, None

    def _is_vertex_inside_area(self, x, y, xc, yc, r):
        if x >= xc - r and x <= xc + r and y >= yc - r and y <= yc + 5:
            return True
        return False

    def _on_cancel_bbox(self, event):
        if self.STATE['clicked']:
            if self.curr_bbox_id:
                self.canvas.delete(self.curr_bbox_id)
                self.bboxId = None
                self.STATE['clicked'] = False
                self.STATE['action'] = CREATE
                self.corner_selected = -1
                self.corner_pos = None

if __name__ == '__main__':
    root = Tk()
    tool = LabelCanvas(root)
    root.resizable(width =  True, height = True)
    root.mainloop()
