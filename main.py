#-------------------------------------------------------------------------------
# Name:        Object bounding box label tool
# Purpose:     Label object bboxes for ImageNet Detection data
# Author:      Qiushi
# Created:     06/06/2014

#
#-------------------------------------------------------------------------------
from __future__ import division
#from Tkinter import *
from tkinter import *
#import tkMessageBox
import tkinter.messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import glob
import random
from os.path import exists, join

# colors for the bboxes
COLORS = ['red', 'blue', 'yellow', 'pink', 'cyan', 'green', 'black']
# image sizes for the examples
SIZE = 256, 256
IMAGES = 'JPEGImages'
LABELS = 'labels'
THUMBNAILS = 'thumbnails'


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("LabelTool")
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
        self.tkimg = None

        # initialize mouse state
        self.STATE = {}
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # reference to bbox
        self.bboxIdList = []
        self.bboxId = None
        self.bboxList = []
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        self.folder_path = Label(self.frame, text="Source Path:")
        self.folder_path.grid(row = 0, column = 0, sticky = E)

        content = StringVar()
        self.folder_path_entry = Entry(self.frame, textvariable=content)
        self.folder_path_entry.grid(row = 0, column = 1, columnspan=3, sticky = W+E)
        content.set('/Users/jtrabucco/Documents/Projects/datasets/Scene_1/train/')
        self.ldBtn = Button(self.frame, text = "Load", command = self.loadDir)
        self.ldBtn.grid(row = 0, column = 4, sticky = W+E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        self.mainPanel.bind("<Motion>", self.mouseMove)
        self.parent.bind("<Escape>", self.cancelBBox)  # press <Espace> to cancel current bbox
        self.parent.bind("s", self.cancelBBox)
        self.parent.bind("a", self.prevImage) # press 'a' to go backforward
        self.parent.bind("d", self.nextImage) # press 'd' to go forward
        self.mainPanel.grid(row = 2, column = 2, rowspan = 4, sticky = W+N)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text = 'Bounding boxes:')
        self.lb1.grid(row = 2, column = 3, columnspan=2,  sticky = W+N)
        self.listbox = Listbox(self.frame, width = 22, height = 12)
        self.listbox.bind("<Double-Button-1>", self.on_click_listbox)
        self.listbox.grid(row = 3, column = 3, columnspan=2, sticky = N)
        #self.btnDel = Button(self.frame, text = 'Delete', command = self.delBBox)
        #self.btnDel.grid(row = 4, column = 2, sticky = W+E+N)
        #self.btnClear = Button(self.frame, text = 'ClearAll', command = self.clearBBox)
        #self.btnClear.grid(row = 5, column = 2, sticky = W+E+N)

        self.lbUpdate = Label(self.frame, text = 'Person Information:')
        self.lbUpdate.grid(row = 4, column=3, columnspan=2,  sticky = W+N)
        
        self.sel_thumbnail = Frame(self.frame, border = 10)
        self.sel_thumbnail.grid(row = 5, column = 2, columnspan=2, rowspan = 3, sticky = N)
        self.sel_thumb_label = Label(self.sel_thumbnail)
        self.sel_thumb_label.pack(side = TOP)

        self.thumbnail = Canvas(self.frame, width = 200, height = 200, bd='5')  
        self.thumbnail.grid(row=5, column=3, columnspan=2, rowspan=3, sticky=N)

        self.sel_bbox_text = StringVar()
        self.sel_bbox_label = Label(self.frame, text='BBox Info:')
        self.sel_bbox_label.grid(row = 9, column = 3,  sticky = N)
        self.sel_bbox_value = Label(self.frame, textvariable=self.sel_bbox_text)
        self.sel_bbox_value.grid(row = 9, column = 4,  sticky = N)

        self.sel_person_id = StringVar()
        self.lblPersonId = Label(self.frame, text = "Person Id:")
        self.lblPersonId.grid(row = 10, column = 3, sticky = N)
        self.entryPersonId = Entry(self.frame, textvariable=self.sel_person_id)
        self.entryPersonId.grid(row = 10, column = 4, sticky = N)
        
        self.sel_hard = StringVar()
        self.lblHard = Label(self.frame, text = "Is Hard?:")
        self.lblHard.grid(row = 11, column = 3, sticky = N)
        self.entryHard = Entry(self.frame, textvariable=self.sel_hard)
        self.entryHard.grid(row = 11, column = 4, sticky = N)

        self.btnAddId = Button(self.frame, text='Update', command=self.on_click_update)
        self.btnAddId.grid(row = 12, column =3, sticky=N)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row = 13, column = 1, columnspan = 2, sticky = W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width = 10, command = self.prevImage)
        self.prevBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width = 10, command = self.nextImage)
        self.nextBtn.pack(side = LEFT, padx = 5, pady = 3)
        self.progLabel = Label(self.ctrPanel, text = "Progress:     /    ")
        self.progLabel.pack(side = LEFT, padx = 5)
        self.tmpLabel = Label(self.ctrPanel, text = "Go to Image No.")
        self.tmpLabel.pack(side = LEFT, padx = 5)
        self.idxEntry = Entry(self.ctrPanel, width = 5)
        self.idxEntry.pack(side = LEFT)
        self.goBtn = Button(self.ctrPanel, text = 'Go', command = self.gotoImage)
        self.goBtn.pack(side = LEFT)

        # example pannel for illustration
        self.egPanel = Frame(self.frame, border = 5)
        self.egPanel.grid(row = 2, column = 0, rowspan = 5, sticky = N)
        self.egPanelAdditional = Frame(self.frame, border = 5)
        self.egPanelAdditional.grid(row = 2, column = 1, rowspan = 5, sticky = N)
        # self.tmpLabel2 = Label(self.egPanel, text = "Gallery:")
        # self.tmpLabel2.pack(side = TOP, pady = 5)
        self.egLabels = []


        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side = RIGHT)

        self.frame.columnconfigure(1, weight = 1)
        self.frame.rowconfigure(4, weight = 1)

        self.person_ids = None
        self.yolo_bboxes = []
        self.bbox_person_ids = []
        self.bbox_text_boxes = []
        self.sel_idx = -1
        self.img_width = 0
        self.img_height = 0
        self.ids_thumbnails = []


    def loadDir(self, dbg = False):
        if not dbg:
            f = self.folder_path_entry.get()

            #s = self.entry.get()
            self.parent.focus()
            #self.category = int(s)
        else:
            s = r'D:\workspace\python\labelGUI'

        self.imageDir = os.path.join(f, '%s' % IMAGES)
        self.thumbnails_dir = os.path.join(f, THUMBNAILS)
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

        # # load example bboxes
        # self.egDir = os.path.join(r'./Examples')
        # if not os.path.exists(self.egDir):
        #     os.mkdir('./Examples')

        # filelist = glob.glob(os.path.join(self.egDir, '*.JPEG'))
        # self.tmp = []
        # self.egList = []
        # random.shuffle(filelist)
        # for (i, f) in enumerate(filelist):
        #     if i == 3:
        #         break
        #     im = Image.open(f)
        #     r = min(SIZE[0] / im.size[0], SIZE[1] / im.size[1])
        #     new_size = int(r * im.size[0]), int(r * im.size[1])
        #     self.tmp.append(im.resize(new_size, Image.ANTIALIAS))
        #     self.egList.append(ImageTk.PhotoImage(self.tmp[-1]))
        #     self.egLabels[i].config(image = self.egList[-1], width = SIZE[0], height = SIZE[1])

        self.loadImage()

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        self.img = self.img.resize((900, 600), Image.ANTIALIAS)

        self.tkimg = ImageTk.PhotoImage(self.img)
        self.mainPanel.config(width = max(self.tkimg.width(), 400), height = max(self.tkimg.height(), 400))
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
        self.progLabel.config(text = "%04d/%04d" %(self.cur, self.total))

        # load labels
        self.img_width, self.img_height = self.img.size
        self.clearBBox()
        self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        print('Image Name: %s' % self.imagename)

        labelname = self.imagename + '.txt'
        self.labelfilename = os.path.join(self.outDir, labelname)
        bbox_cnt = 0
        self.load_bounding_boxes(self.labelfilename, self.img_width, self.img_height)

                    # print('%d: %s' % (i, line))
 #                     if i == 0:
 #                         bbox_cnt = int(line.strip())
 #                         continue
 #                     tmp = [int(t.strip()) for t in line.split()]
 # ##                    print(tmp)  # By Tomonori12
 #                     self.bboxList.append(tuple(tmp))
 #                     tmpId = self.mainPanel.create_rectangle(tmp[0], tmp[1], \
 #                                                             tmp[2], tmp[3], \
 #                                                             width = 2, \
 #                                                             outline = COLORS[(len(self.bboxList)-1) % len(COLORS)])
 #                     self.bboxIdList.append(tmpId)
 #                     self.listbox.insert(END, '(%d, %d) -> (%d, %d)' %(tmp[0], tmp[1], tmp[2], tmp[3]))
 #                     self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])


    def load_bounding_boxes(self, filename, width, height):
        self.clearBBox()

        if os.path.exists(filename):
            with open(filename) as f:
                for (i, line) in enumerate(f):
                    vals = [t.strip() for t in line.split()]
                    p_id = int(vals[0])
                    
                    yolo_bbox = [float(t) for t in vals[1:]]
                    self.yolo_bboxes.append(yolo_bbox)

                    bbox = self.convertYoloToRegular([width, height], yolo_bbox)
                    self.bboxList.append(tuple(bbox))

                    outline_color = COLORS[(len(self.bboxList)-1) % len(COLORS)]
                    tmpId = self.mainPanel.create_rectangle(bbox[0], bbox[1], \
                                                            bbox[2], bbox[3], \
                                                            width = 2, \
                                                            outline = outline_color)
                    tmpTxtId = self.mainPanel.create_text(bbox[0] + 10, bbox[1] + 10, fill=outline_color, font="Times 16 bold", text=str(p_id))
                    self.bbox_text_boxes.append(tmpTxtId)

                    self.bbox_person_ids.append(p_id)
                    self.bboxIdList.append(tmpId)
                    self.listbox.insert(END, '%d: (%d, %d) -> (%d, %d)' %(p_id, bbox[0], bbox[1], bbox[2], bbox[3]))
                    self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = outline_color) 
        else:
            print('File does not exist')       


    def saveImage(self):
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' %len(self.bboxList))
            for bbox in self.bboxList:
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' %(self.cur))  # By Tomonori12


    def mouseClick(self, event):
        if self.STATE['click'] == 0:
            self.STATE['x'], self.STATE['y'] = event.x, event.y
        else:
            x1, x2 = min(self.STATE['x'], event.x), max(self.STATE['x'], event.x)
            y1, y2 = min(self.STATE['y'], event.y), max(self.STATE['y'], event.y)
            self.bboxList.append((x1, y1, x2, y2))
            self.bboxIdList.append(self.bboxId)
            self.bboxId = None
            self.listbox.insert(END, '(%d, %d) -> (%d, %d)' %(x1, y1, x2, y2))
            self.listbox.itemconfig(len(self.bboxIdList) - 1, fg = COLORS[(len(self.bboxIdList) - 1) % len(COLORS)])
        self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text = 'x: %d, y: %d' %(event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width = 2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width = 2)
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
            self.bboxId = self.mainPanel.create_rectangle(self.STATE['x'], self.STATE['y'], \
                                                            event.x, event.y, \
                                                            width = 2, \
                                                            outline = COLORS[len(self.bboxList) % len(COLORS)])

    def cancelBBox(self, event):
        if 1 == self.STATE['click']:
            if self.bboxId:
                self.mainPanel.delete(self.bboxId)
                self.bboxId = None
                self.STATE['click'] = 0

    def delBBox(self):
        sel = self.listbox.curselection()
        if len(sel) != 1 :
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.bboxIdList[idx])
        self.bboxIdList.pop(idx)
        self.bboxList.pop(idx)
        self.listbox.delete(idx)

    def clearBBox(self):
        for idx in range(len(self.bboxIdList)):
            self.mainPanel.delete(self.bboxIdList[idx])
        for idx in range(len(self.bbox_text_boxes)):
            self.mainPanel.delete(self.bbox_text_boxes[idx])
        self.listbox.delete(0, len(self.bboxList))
        self.bboxIdList = []
        self.bboxList = []
        self.yolo_bbox = []
        self.bbox_person_ids = []

    def prevImage(self, event = None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event = None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def convertYoloToRegular(self, size, box):
        x2 = int(((2*size[0]*float(box[0]))+(size[0]*float(box[2])))/2)
        x1 = int(((2*size[0]*float(box[0]))-(size[0]*float(box[2])))/2)
        y2 = int(((2*size[1]*float(box[1]))+(size[1]*float(box[3])))/2)
        y1 = int(((2*size[1]*float(box[1]))-(size[1]*float(box[3])))/2)
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

    def on_click_listbox(self, event):
        idx = int(self.listbox.curselection()[0])
        self.sel_idx = idx
        self.sel_id = self.listbox.get(idx).split(":")[0]
        self.sel_person_id.set(str(self.sel_id))
        self.sel_bbox_text.set(self.listbox.get(idx))

        bbox = self.bboxList[idx]
        print(bbox)
        print(self.img.size)
        self.cropped = self.img.crop( ( bbox[0], bbox[1], bbox[2] , bbox[3] ) )
        self.cropped.thumbnail((200, 200), Image.ANTIALIAS)

        self.selected_thumbnail = ImageTk.PhotoImage(self.cropped)
        cw, ch = self.cropped.size
        self.thumbnail.create_image(cw, ch, image=self.selected_thumbnail) 

    def on_click_update(self):
        self.bbox_person_ids[self.sel_idx] = self.entryPersonId.get()

        with open(self.labelfilename, 'w') as label_file:
            for (pid, bbox) in zip(self.bbox_person_ids, self.yolo_bboxes):
                label_file.write('%d %f %f %f %f\n' % (int(pid), float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])))
        self.save_thumbnail(self.sel_id, self.cropped)
        self.load_bounding_boxes(self.labelfilename, self.img_width, self.img_height)

    def save_thumbnail(self, id, image):
        if not exists(self.thumbnails_dir):
            os.mkdir(self.thumbnails_dir)
        
        filename = '%s.jpg' % id
        if filename not in os.listdir(self.thumbnails_dir):
            image.save(join(self.thumbnails_dir, filename))

        self.display_thumbnails()
        return

    def display_thumbnails(self):
        self.ids_thumbnails = []
        for th in self.egLabels: th.destroy()
        if not exists(self.thumbnails_dir): return

        thumbs = [x for x in os.listdir(self.thumbnails_dir) if x != '.DS_Store']
        thumbs.sort()

        for idx, f in enumerate(thumbs):            
            self.egLabels.append(Label(self.egPanel))
            self.egLabels[-1].pack(side = TOP)

            p = join(self.thumbnails_dir, f)
            im = Image.open(p)
            im = im.resize((50, 50), Image.ANTIALIAS)

            img_t = ImageDraw.Draw(im)
            img_t.text((0, 0), f[:-4],(0,255,0))

            w, h = im.size
            self.ids_thumbnails.append(ImageTk.PhotoImage(im))
            self.egLabels[-1].config(image=self.ids_thumbnails[-1], width=w, height=h)
            

if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.resizable(width =  True, height = True)
    root.mainloop()
