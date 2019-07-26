#-------------------------------------------------------------------------------
# Modified Labeling Tool for Person Reidentification based on:
#       Name:        Object bounding box label tool
#       Purpose:     Label object bboxes for ImageNet Detection data
#       Author:      Qiushi
#       Created:     06/06/2014
#-------------------------------------------------------------------------------

from __future__ import division
import pdb
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
from tkinter.messagebox import showerror
import os
import glob
import random
from os.path import exists, join, isdir

# colors for the bboxes
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 256, 256
IMAGES = 'JPEGImages'
LABELS = 'labels'
THUMBNAILS = 'thumbnails'

# Canvas constants
CLICKED = True
RADIUS = 5
TOP_LEFT = 0
BOTTOM_RIGHT = 1
EDIT = 'edit'
CREATE = 'create'

SOURCE_PATH = '/Users/jtrabucco/Documents/Projects/datasets'

class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("Labeling Tool")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = FALSE, height = FALSE)

        # initialize global state
        self.imageDir = ''
        self.imageList= []
        self.egDir = ''
        self.egList = []
        self.outDir = ''
        self.cur = 0
        self.total = 0
        self.category = 0
        self.imagename = ''
        self.labelfilename = ''

        self._init_mouse_state()
        self._init_vars()
        self._create_data_sel_gui()
        self._create_canvas()

        # self.parent.bind("e", self.nextImage)
        # self.parent.bind("q", self.prevImage) # press 'a' to go backforward
        #self.parent.bind("w", self.on_click_update)
        #self.parent.bind("d", self.nextImage) # press 'd' to go forward
        # self.canvas.grid(row = 3, column = 1, rowspan = 4, sticky = W+N)

        self._create_listbox_gui()
        self._create_info_panel_gui()
        self._create_img_nav_gui()
        self._create_gallery_gui()

        self.egLabels = []

        # display mouse position
        self.disp = Label(self.ctr_panel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

        self.person_ids = None
        self.yolo_bboxes = []
        self.standing_vals = []
        self.full_body_vals = []
        self.sel_idx = -1
        self.img_width = 0
        self.img_height = 0

    def _init_mouse_state(self):
        self.STATE = {}
        self.STATE['clicked'] = not CLICKED
        self.STATE['action'] = CREATE
        self.STATE['x'], self.STATE['y'] = 0, 0    

    def _restart_vars(self):
        self.bboxes_ids = []
        self.bboxes = [] 
        self.bbox_text_boxes = []
        self.handlers = {}
        self.standing_vals = []
        self.bbox_person_ids = []
        self.full_body_vals = []
        self.yolo_bboxes = []
        self.handlers = {}

    def _init_vars(self):
        self.bboxes_ids = []        # id references to bboxes managed by Tkinter        
        self.bboxes = []            # (x1,y1,x2,y2) for all ids in bboxes_ids
        self.bbox_text_boxes = []   # id references of bbox person_id labels
        self.curr_bbox_id = None    # current bbox being drawn
        self.corner_selected = -1   # flag bounding box corner selected or not
        self.corner_pos = None      # indicate TOP_LEFT or BOTTOM_RIGHT handle
        self.handlers = {}          # references to the circles in the rectangle corners
        self.r = 5
        self.bbox_person_ids = []

        self.gal_nav_idx = 1
        self.thumbnail_ids = []

        self.remaining_unlabeled = 0

        self.hl = None              # horizontal line (not used now)
        self.vl = None
        self.tkimg = None

    def _create_data_sel_gui(self):
        self.lbl_folder_path = Label(self.frame, text="Source Path:")
        self.lbl_folder_path.grid(row = 0, column = 0, sticky = E)

        source_folder_path = StringVar()
        self.txt_folder_path = Entry(self.frame, textvariable=source_folder_path)
        self.txt_folder_path.grid(row = 0, column = 1, columnspan=3, sticky = W+E)
        source_folder_path.set(SOURCE_PATH)

        self.btn_load_scenes = Button(self.frame, text = "Load Scenes", command = self.loadDir)
        self.btn_load_scenes.grid(row = 0, column = 4, sticky = W+E)

        self.sel_scene = StringVar()
        self.lbl_scene = Label(self.frame, text="Scene:")
        self.lbl_scene.grid(row = 1, column = 0, sticky = E)
        self.ddl_scene = OptionMenu(self.frame, self.sel_scene, "")
        self.ddl_scene.grid(row=1, column=1)

        self.sel_subdir = StringVar()
        self.lbl_subdir = Label(self.frame, text="Folder:")
        self.lbl_subdir.grid(row=1, column=2, sticky=E)

        self.btn_load_data = Button(self.frame, text = "Load Data", command = self.load_data)
        self.btn_load_data.grid(row = 1, column = 4, sticky = W+E)

    def _create_canvas(self):
        self.canvas = Canvas(self.frame, cursor='tcross')
        self.canvas.grid(row = 3, column = 1, rowspan = 4, sticky = W+N)
        # self.canvas.pack(fill=BOTH, expand=True)

        self.canvas.bind("<Button-1>", self._on_mouse_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.parent.bind("<Escape>", self._on_cancel_bbox)

    def _create_listbox_gui(self):
        lb_pnl = Frame(self.frame)
        lb_pnl.grid(row=3, column=3, columnspan=2, sticky=N)

        self.lb1 = Label(lb_pnl, text = 'Bounding boxes:')
        # self.lb1.grid(row = 3, column = 3, columnspan=2,  sticky = W+N)
        self.lb1.pack()

        self.listbox = Listbox(lb_pnl, width = 22, height = 15, bg='gray')
        self.listbox.bind("<Double-Button-1>", self.on_click_listbox)
        self.listbox.pack()
        # self.listbox.grid(row = 4, column = 3, columnspan=2, sticky = N)
        self.btnDel = Button(lb_pnl, text = 'Delete', command = self._on_delete_click)
        self.btnDel.pack(fill=X)
        # self.btnDel.grid(row = 5, column = 3, sticky = W+E+N)
        #self.btnClear = Button(lb_pnl, text = 'ClearAll', command = self.clearBBox)
        #self.btnClear.pack(fill=X)
        # self.btnClear.grid(row = 6, column = 3, sticky = W+E+N)

    def _create_info_panel_gui(self):
        self.action_panel = Frame(self.frame)
        self.action_panel.grid(row=5, column=3, columnspan=2, sticky=N)
        
        self.lbl_sel_item = Label(self.action_panel, text = 'Selected Item')
        self.lbl_sel_item.pack()

        self.thumbnail = Canvas(self.action_panel, width = 200, height = 200, bd='5', bg='black')  
        self.thumbnail.pack()

        pnl1 = Frame(self.action_panel)
        pnl1.pack()

        self.lbl_bbox = Label(pnl1, text='BBox:')
        self.lbl_bbox.pack(side=LEFT)
        self.sel_bbox_val = StringVar()
        self.lbl_sel_bbox_val = Label(pnl1, textvariable=self.sel_bbox_val)
        self.lbl_sel_bbox_val.pack(side=LEFT)

        pnl2 = Frame(self.action_panel)
        pnl2.pack()

        self.lbl_person_id = Label(pnl2, text = "Person Id:")
        self.lbl_person_id.pack(side=LEFT)
        self.sel_person_id = StringVar()
        self.txt_person_id = Entry(pnl2, width=5, textvariable=self.sel_person_id, vcmd=self.val_only_integer)
        self.txt_person_id.pack(side=LEFT)
        
        self.standing_val = IntVar()
        self.chk_is_standing = Checkbutton(self.action_panel, text='Person is standing?', variable=self.standing_val)
        self.chk_is_standing.pack()

        self.full_body_val = IntVar()
        pnl_rbs = Frame(self.action_panel)
        pnl_rbs.pack(fill=X)
        Radiobutton(pnl_rbs, text="Full", variable=self.full_body_val, value=0).pack(side=LEFT)
        Radiobutton(pnl_rbs, text="Half", variable=self.full_body_val, value=1).pack(side=LEFT)
        Radiobutton(pnl_rbs, text="Head", variable=self.full_body_val, value=2).pack(side=LEFT)

        # self.chk_see_fullbody = Checkbutton(self.action_panel, text='Can see full body?', variable=self.full_body_val)
        # self.chk_see_fullbody.pack()

        self.replace_thmb_val = IntVar()
        self.chk_replace_thumbnail = Checkbutton(self.action_panel, text='Replace Thumbnail?', variable=self.replace_thmb_val)
        self.chk_replace_thumbnail.pack()

        self.btn_update_data = Button(self.action_panel, text='Update', command=self.on_click_update)
        self.btn_update_data.pack(fill=X)

    def _create_img_nav_gui(self):
        self.ctr_panel = Frame(self.frame)
        self.ctr_panel.grid(row = 7, column = 1, columnspan = 2, sticky = W+E)
        self.lbl_progress = Label(self.ctr_panel, text = "Progress:     /    ")
        self.lbl_progress.pack(side = LEFT, padx = 5)
        self.btn_prev = Button(self.ctr_panel, text='<< Prev', width = 10, command = self.prevImage)
        self.btn_prev.pack(side = LEFT, padx = 5, pady = 3)
        self.btn_next = Button(self.ctr_panel, text='Next >>', width = 10, command = self.nextImage)
        self.btn_next.pack(side = LEFT, padx = 5, pady = 3)
        self.lbl_go_to = Label(self.ctr_panel, text = "Go to Image No.")
        self.lbl_go_to.pack(side = LEFT, padx = 5)
        self.txt_img_number = Entry(self.ctr_panel, width = 5)
        self.txt_img_number.pack(side = LEFT)
        self.btn_go2image = Button(self.ctr_panel, text = 'Go', command = self.gotoImage)
        self.btn_go2image.pack(side = LEFT)

        self.remaining_val = StringVar()
        self.lbl_remaining = Label(self.ctr_panel, text= "Remaining unlabeled: X", textvariable=self.remaining_val)
        self.lbl_remaining.pack(side=RIGHT)

    def _create_gallery_gui(self):
        self.gallery_panel = Frame(self.frame, border = 5)
        self.gallery_panel.grid(row = 3, column = 0, rowspan = 5, sticky = N)
        # self.egPanelAdditional = Frame(self.frame, border = 5)
        # self.egPanelAdditional.grid(row = 2, column = 1, rowspan = 5, sticky = N)
        
        self.gal_btns_pnl = Frame(self.frame)
        self.gal_btns_pnl.grid(row = 7, column = 0, sticky = W+E)
        self.lbl_gallery = Label(self.gallery_panel, text = "Gallery:")
        self.lbl_gallery.pack(side = TOP, pady = 5)
        self.btn_prev_gal = Button(self.gal_btns_pnl, text='<', width=2, command = self.on_click_prev_ten)
        self.btn_prev_gal.pack(side=LEFT, padx=0, pady=2)
        self.btn_next_gal = Button(self.gal_btns_pnl, text='>', width=2, command = self.on_click_next_ten)
        self.btn_next_gal.pack(side=RIGHT, padx=0, pady=2)

    def _add_handlers(self, bbox_id, x1, y1, x2, y2):
        id_tl = self.canvas.create_oval(x1 - self.r, y1 - self.r, x1 + self.r, y1 + self.r, fill='yellow', outline='black')
        id_br = self.canvas.create_oval(x2 - self.r, y2 - self.r, x2 + self.r, y2 + self.r, fill='yellow', outline='black')
        self.handlers[bbox_id] = [id_tl, id_br]

    def _add_bbox(self, event, new_person_id = 0, standing_val = 0, fb_val = 0):
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

        # self._add_handlers(self.curr_bbox_id, x1, y1, x2, y2)
        self.bboxes.append((x1, y1, x2, y2))
        self.bboxes_ids.append(self.curr_bbox_id)
        self.yolo_bboxes.append(self.convertRegularToYolo((self.img_width, self.img_height), (x1,y1,x2,y2)))
        self.bbox_person_ids.append(new_person_id)

        outline = COLORS[(len(self.bboxes_ids) - 1) % len(COLORS)]
        self.listbox.insert(END, '%d: (%d, %d) -> (%d, %d)' % (0, x1, y1, x2, y2))
        self.listbox.itemconfig(len(self.bbox_person_ids) - 1, fg = outline)

        self.standing_vals.append(standing_val)
        self.full_body_vals.append(fb_val)
        tkinter_label_id = self.canvas.create_text(x1+ 10, y1 + 10, fill=outline, font="Times 16 bold", text='0')
        self.bbox_text_boxes.append(tkinter_label_id)

        print(self.bbox_person_ids)
        self._save_to_file()

        self.curr_bbox_id = None
        return x1, y1, x2, y2, tmp_id

    def _del_bbox(self, bbox_id):
        # pdb.set_trace()
        self.canvas.delete(bbox_id)
        if bbox_id in self.handlers.keys():
            for c_id in self.handlers[bbox_id]:
                self.canvas.delete(c_id)
            del self.handlers[bbox_id]      # remove handlers from canvas
        
        idx = self.bboxes_ids.index(bbox_id)
        del self.bboxes_ids[idx]        # remove tkinter rectangle id
        del self.bboxes[idx]            # remove bounding box data
        del self.bbox_text_boxes[idx]   # remove tkinter text from canvas
        del self.standing_vals[idx]     # remove from standing array
        del self.full_body_vals[idx]    # remove from full body array
        del self.bbox_person_ids[idx]
        del self.yolo_bboxes[idx]
        self.canvas.delete(self.bbox_text_boxes[idx])

        self._save_to_file()

        self.load_bounding_boxes(self.labelfilename, self.img_width, self.img_height)

    def _edit_box(self, event):
        sel_listbox_idx = self.sel_idx
        person_id = self.txt_person_id.get()
        bbox_id = self.bboxes_ids[sel_listbox_idx]

        self._add_bbox(event, new_person_id = int(person_id), \
            standing_val = self.standing_vals[sel_listbox_idx], \
            fb_val = self.full_body_vals[sel_listbox_idx])
        self._del_bbox(bbox_id)


    def _on_mouse_click_create(self, event):
        if not self.STATE['clicked']:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
            self.corner_selected, self.corner_pos = self._on_corner_selected(event.x, event.y, self.r)
            if self.corner_selected != -1:
                print('going to edit mode')
                self.STATE['action'] = EDIT
        else:
            self._add_bbox(event)
    
    def _on_mouse_click_edit(self, event):
        # always performed on clicked so reset to CREATE afterwards
        # self._add_bbox(event)
        # self._del_bbox(self.bboxes_ids[self.corner_selected])
        self._edit_box(event)
        self.STATE['action'] = CREATE
        self.corner_selected = -1

    def loadDir(self, dbg = False):        
        f = self.txt_folder_path.get()
        self.root = f
        self.parent.focus()
        self.load_scenes()

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.img = self.img.resize((900, 650), Image.ANTIALIAS)

        self.tkimg = ImageTk.PhotoImage(self.img)
        self.canvas.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.canvas.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.lbl_progress.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.img_width, self.img_height = self.img.size
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        print('Image Name: %s' % self.imagename)

        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        self.load_bounding_boxes(self.labelfilename, self.img_width, self.img_height)


    def load_scenes(self):
        scenes = [f for f in os.listdir(self.root) if isdir(join(self.root, f))]
        self.sel_scene = StringVar()
        self.ddl_scene.destroy()
        self.ddl_scene = OptionMenu(self.frame, self.sel_scene, *scenes, command=self.load_subdirs)
        self.ddl_scene.grid(row=1, column=1, sticky=W+E)
        self.clearBBox()
        self.clear_selection()
        self.canvas.delete(ALL)

    def load_subdirs(self, scene):
        subdirs = [f for f in os.listdir(join(self.root, scene)) if isdir(join(self.root, scene, f))]
        self.subdir_ddl = OptionMenu(self.frame, self.sel_subdir, *subdirs, command=self.on_change_load_dirs)
        self.subdir_ddl.grid(row=1, column=3, sticky=W+E)
        self.clearBBox()
        self.clear_selection()
        self.canvas.delete(ALL)

    def on_change_load_dirs(self, value):
        self.clearBBox()
        self.clear_selection()
        self.canvas.delete(ALL)

    def load_data(self):
        f = join(self.root, self.sel_scene.get(), self.sel_subdir.get())
        self.imageDir = os.path.join(f, '%s' % IMAGES)
        self.thumbnails_dir = os.path.join(self.root, THUMBNAILS)
        print('Image folder %s' % self.imageDir)

        self.imageList = glob.glob(os.path.join(self.imageDir, '*.jpg'))
        self.imageList.sort()  # By Tomonori12
        if len(self.imageList) == 0:
            print('No .JPEG images found in the specified dir!')  # By Tomonori12
            return

        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)

         # set up output dir
        self.outDir = os.path.join(f, '%s' % LABELS)
        self.display_thumbnails()
        self.loadImage()

    def load_bounding_boxes(self, filename, width, height):
        self.clearBBox()
        self._restart_vars()
        self._delete_all_handlers()
        
        self.remaining_unlabeled = 0

        if os.path.exists(filename):
            print(filename)
            with open(filename) as f:
                for line in f:
                    vals = [t.strip() for t in line.split()]

                    # Load the standing features, new label files are not complete
                    if len(vals) == 5:
                        standing = 0
                        see_full_body = 0
                    else:
                        standing = int(vals[5])
                        see_full_body = int(vals[6])
                    self.standing_vals.append(standing)
                    self.full_body_vals.append(see_full_body)

                    p_id = int(vals[0])
                    if p_id == 0:
                        self.remaining_unlabeled += 1
                    
                    yolo_bbox = [float(t) for t in vals[1:]]
                    self.yolo_bboxes.append(yolo_bbox)

                    bbox = self.convertYoloToRegular([width, height], yolo_bbox)
                    self.bboxes.append(tuple(bbox))

                    outline_color = COLORS[(len(self.bboxes)-1) % len(COLORS)]
                    tkinter_bbox_id = self.canvas.create_rectangle(bbox[0], bbox[1], bbox[2], bbox[3], width = 2, outline = outline_color)
                    tkinter_label_id = self.canvas.create_text(bbox[0] + 10, bbox[1] + 10, fill=outline_color, font="Times 16 bold", text=str(p_id))
                    
                    self.bbox_person_ids.append(p_id)
                    self.bboxes_ids.append(tkinter_bbox_id)
                    self.bbox_text_boxes.append(tkinter_label_id)
                    self.listbox.insert(END, '%d: (%d, %d) -> (%d, %d)' %(p_id, bbox[0], bbox[1], bbox[2], bbox[3]))
                    self.listbox.itemconfig(len(self.bbox_person_ids) - 1, fg = outline_color) 
            self.remaining_val.set('Remaining unlabeled: %d' % self.remaining_unlabeled)
        else:
            print('File does not exist')       


    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' %len(self.bboxes))
            for bbox in self.bboxes:
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' %(self.cur))


    def _on_mouse_click(self, event):
        if self.STATE['action'] == CREATE:
            self._on_mouse_click_create(event)
        else:
            self._on_mouse_click_edit(event)
        self.STATE['clicked'] = not self.STATE['clicked']
        
    def _on_mouse_move(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.canvas.delete(self.hl)
            self.hl = self.canvas.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.canvas.delete(self.vl)
            self.vl = self.canvas.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        
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

    def _on_delete_click(self):
        idx = int(self.listbox.curselection()[0])
        self._del_bbox(self.bboxes_ids[idx])
        # self.canvas.delete(self.bboxes_ids[idx])
        # self.bboxes_ids.pop(idx)
        # self.bboxes.pop(idx)
        # self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxes_ids)):
            self.canvas.delete(self.bboxes_ids[idx])
        for idx in range(len(self.bbox_text_boxes)):
            self.canvas.delete(self.bbox_text_boxes[idx])
        self.listbox.delete(0, len(self.bboxes))

    def prevImage(self, event = None):
        self.clear_selection()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.clear_selection()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        self.clear_selection()
        idx = int(self.txt_img_number.get())
        if 1 <= idx and idx <= self.total:
            self.cur = idx
            self.loadImage()

    def convertYoloToRegular(self, size, box):
        x2 = int(((2*size[0]*float(box[0]))+(size[0]*float(box[2])))/2)
        x1 = int(((2*size[0]*float(box[0]))-(size[0]*float(box[2])))/2)
        y2 = int(((2*size[1]*float(box[1]))+(size[1]*float(box[3])))/2)
        y1 = int(((2*size[1]*float(box[1]))-(size[1]*float(box[3])))/2)
        return (x1,y1,x2,y2)

    def convertRegularToYolo(self, size, box):
        x1 = (box[0] + box[2])/(2 * size[0])
        x2 = (box[2] - box[0])/size[0]
        y1 = (box[1] + box[3])/(2 * size[1])
        y2 = (box[3] - box[1])/size[1]
        return (x1,y1,x2,y2)

    def add_person_id(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
            # just do something if a bbox is selected
            return

        if sel[0] > 0:
            print('The box already has an ID')
            return

        if self.person_ids == None:
            self.person_ids = [1]
        new_id = self.person_ids[-1]

    def val_only_integer(self, v):
        print(v)
        return False

    def _delete_all_handlers(self):
        for k in self.handlers.keys():
            for v in self.handlers[k]:
                self.canvas.delete(v)
        self.handlers = {}

    def on_click_listbox(self, event):
        idx = int(self.listbox.curselection()[0])
        print("You clicked %d listbox item"  % idx)
        self.sel_idx = idx
        bbox = self.bboxes[idx]

        # show handlers
        self._delete_all_handlers()
        bbox_id = self.bboxes_ids[idx]
        self._add_handlers(bbox_id, bbox[0], bbox[1], bbox[2], bbox[3])

        self.sel_id = self.listbox.get(idx).split(":")[0]
        self.sel_person_id.set(str(self.sel_id))
        self.sel_bbox_val.set(str(bbox))
        self.standing_val.set(self.standing_vals[self.sel_idx])
        self.full_body_val.set(self.full_body_vals[self.sel_idx])

        self.cropped = self.img.crop( ( bbox[0], bbox[1], bbox[2] , bbox[3] ) )
        self.cropped.thumbnail((200, 200), Image.ANTIALIAS)

        self.selected_thumbnail = ImageTk.PhotoImage(self.cropped)
        cw, ch = self.cropped.size
        self.thumbnail.create_image(cw, ch, image=self.selected_thumbnail) 

    def on_click_update(self, event=None):
        self.bbox_person_ids[self.sel_idx] = int(self.txt_person_id.get())
        self.sel_id = self.txt_person_id.get()

        self.full_body_vals[self.sel_idx] = int(self.full_body_val.get())
        self.standing_vals[self.sel_idx] = int(self.standing_val.get()) 
        self._save_to_file()
        print(self.bbox_person_ids)
        
        if int(self.sel_id) > 0: 
            self.save_thumbnail(self.sel_id, self.cropped, self.replace_thmb_val.get())
        self.load_bounding_boxes(self.labelfilename, self.img_width, self.img_height)

    def _save_to_file(self):
        with open(self.labelfilename, 'w') as label_file:
            for (pid, bbox, fb, sv) in zip(self.bbox_person_ids, self.yolo_bboxes, self.full_body_vals, self.standing_vals):
                label_file.write('%s %f %f %f %f %d %d\n' % (str(pid).zfill(3), float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]), sv, fb))

    def save_thumbnail(self, id, image, replace):
        if not exists(self.thumbnails_dir):
            os.mkdir(self.thumbnails_dir)
        
        filename = '%s.jpg' % id.zfill(3)
        if filename not in os.listdir(self.thumbnails_dir) or replace:
            image.save(join(self.thumbnails_dir, filename))

        self.display_thumbnails()

    def display_thumbnails(self):
        self.thumbnail_ids = []
        for th in self.egLabels: th.destroy()
        if not exists(self.thumbnails_dir): return

        thumbs = self.get_gallery_items(self.gal_nav_idx)

        for idx, f in enumerate(thumbs):            
            self.egLabels.append(Label(self.gallery_panel))
            self.egLabels[-1].pack(side = TOP)

            p = join(self.thumbnails_dir, f)
            im = Image.open(p)
            im = im.resize((50, 50), Image.ANTIALIAS)

            img_t = ImageDraw.Draw(im)
            pid = str(int(f[:-4]))
            img_t.rectangle([(0, 0), (15, 10)], fill='white')
            img_t.text((1, 0), pid,(0,0,0))

            w, h = im.size
            self.thumbnail_ids.append(ImageTk.PhotoImage(im))
            self.egLabels[-1].config(image=self.thumbnail_ids[-1], width=w, height=h)
    
    def get_gallery_items(self, gal_idx):
        thumbs = [x for x in os.listdir(self.thumbnails_dir) if x != '.DS_Store']
        thumbs = thumbs[10*(gal_idx-1):10*(gal_idx-1)+10]
        thumbs.sort()
        return thumbs

    def on_click_prev_ten(self):
        if self.gal_nav_idx == 1:
            return
        self.gal_nav_idx -= 1
        self.display_thumbnails()

    def on_click_next_ten(self):
        if 10 * self.gal_nav_idx > self.total:
            return
        self.gal_nav_idx += 1
        self.display_thumbnails()

    def clear_selection(self):
        self.sel_idx = -1
        self.standing_val.set(0)
        self.full_body_val.set(0)
        self.replace_thmb_val.set(0)
        self.sel_person_id.set('')
        self.thumbnail.delete(ALL)
        self.sel_bbox_val.set('')
        self.remaining_unlabeled = 0
        self.yolo_bboxes = []
        self.bbox_person_ids = []
        self.bbox_text_boxes = []
        self.standing_vals = []
        self.full_body_vals = []


if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width =  True, height = True)
    root.mainloop()
