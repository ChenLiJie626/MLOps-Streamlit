import sys, platform
import moderngl
import numpy as np
import wx, math
import wx.glcanvas as glcanvas
from .manager import *
import os.path as osp
from wx.lib.pubsub import pub
from .util import *

class Canvas3D(glcanvas.GLCanvas):
    def __init__(self, parent, manager=None):
        attribList = attribs = (glcanvas.WX_GL_CORE_PROFILE, glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24)
        glcanvas.GLCanvas.__init__(self, parent, -1, attribList=attribList)
        self.init = False
        self.context = glcanvas.GLContext(self)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.manager = self.manager = Manager() if manager is None else manager
        self.size = None

        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_MOTION, self.OnMouseMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.lastx, self.lasty = None, None
        #self.update()
        #print('init===========')

    def InitGL(self):
        self.manager.on_ctx()
        self.DoSetViewport()
        self.manager.reset()

    def OnDraw(self):
        self.manager.set_viewport(0, 0, self.Size.width, self.Size.height)
        #self.manager.count_mvp()
        self.manager.draw()
        self.SwapBuffers()

    def OnSize(self, event):
        wx.CallAfter(self.DoSetViewport)
        event.Skip()

    def DoSetViewport(self):
        size = self.size = self.GetClientSize()
        self.SetCurrent(self.context)
        if not self.manager is None and not self.manager.ctx is None:
            self.manager.set_viewport(0, 0, self.Size.width, self.Size.height)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        self.SetCurrent(self.context)
        #print(self, '=====', self.init)
        if not self.init:
            self.InitGL()
            self.init = True
        self.OnDraw()

    def OnMouseDown(self, evt):
        self.CaptureMouse()
        self.lastx, self.lasty = evt.GetPosition()

    def OnMouseUp(self, evt):
        self.ReleaseMouse()

    def OnMouseMotion(self, evt):
        self.SetFocus()
        if evt.Dragging() and evt.LeftIsDown():
            x, y = evt.GetPosition()
            dx, dy = x-self.lastx, y-self.lasty
            self.lastx, self.lasty = x, y
            angx = self.manager.angx - dx/200
            angy = self.manager.angy + dy/200
            self.manager.set_pers(angx=angx, angy=angy)
            self.Refresh(False)
        if evt.Dragging() and evt.RightIsDown():
            light = self.manager.light
            x, y = evt.GetPosition()
            dx, dy = x-self.lastx, y-self.lasty
            self.lastx, self.lasty = x, y
            angx, angy = dx/200, dy/200
            vx, vy, vz = self.manager.light
            ay = math.asin(vz/math.sqrt(vx**2+vy**2+vz**2))-angy
            xx = math.cos(angx)*vx - math.sin(angx)*vy
            yy = math.sin(angx)*vx + math.cos(angx)*vy
            ay = max(min(math.pi/2-1e-4, ay), -math.pi/2+1e-4)
            zz, k = math.sin(ay), math.cos(ay)/math.sqrt(vx**2+vy**2)
            self.manager.set_light((xx*k, yy*k, zz))
            self.Refresh(False)

    def save_bitmap(self, path):
        context = wx.ClientDC( self )
        memory = wx.MemoryDC( )
        x, y = self.ClientSize
        bitmap = wx.Bitmap( x, y, -1 )
        memory.SelectObject( bitmap )
        memory.Blit( 0, 0, x, y, context, 0, 0)
        memory.SelectObject( wx.NullBitmap)
        bitmap.SaveFile( path, wx.BITMAP_TYPE_PNG )

    def save_stl(self, path):
        from stl import mesh
        objs = self.manager.objs.values()
        vers = [i.vts[i.ids] for i in objs if isinstance(i, Surface)]
        vers = np.vstack(vers)
        model = mesh.Mesh(np.zeros(vers.shape[0], dtype=mesh.Mesh.dtype))
        model.vectors = vers
        model.save(path)

    def OnMouseWheel(self, evt):
        k = 0.9 if evt.GetWheelRotation()>0 else 1/0.9
        self.manager.set_pers(l=self.manager.l*k)
        self.Refresh(False)
        #self.update()
        
def make_bitmap(bmp):
    img = bmp.ConvertToImage()
    img.Resize((20, 20), (2, 2))
    return img.ConvertToBitmap()

class Viewer3D(wx.Panel):
    def __init__( self, parent, manager=None):
        wx.Panel.__init__(self, parent, id = wx.ID_ANY, pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.TAB_TRAVERSAL )
        #self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
        sizer = wx.BoxSizer( wx.VERTICAL )
        self.canvas = Canvas3D(self, manager)
        self.toolbar = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize)
        tsizer = wx.BoxSizer( wx.HORIZONTAL )

        root = osp.abspath(osp.dirname(__file__))

        #self.SetIcon(wx.Icon('data/logo.ico', wx.BITMAP_TYPE_ICO))

        self.btn_x = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap( osp.join(root, 'imgs/x-axis.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_x, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        self.btn_y = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap( osp.join(root, 'imgs/y-axis.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_y, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        self.btn_z = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap( osp.join(root, 'imgs/z-axis.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_z, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        tsizer.Add(wx.StaticLine( self.toolbar, wx.ID_ANY,  wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL), 0, wx.ALL|wx.EXPAND, 2 )
        self.btn_pers = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap( osp.join(root, 'imgs/isometric.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_pers, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        self.btn_orth = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap( osp.join(root, 'imgs/parallel.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_orth, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        tsizer.Add(wx.StaticLine( self.toolbar, wx.ID_ANY,  wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL), 0, wx.ALL|wx.EXPAND, 2 )
        self.btn_open = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap(osp.join(root, 'imgs/open.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_open, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        self.btn_stl = wx.BitmapButton( self.toolbar, wx.ID_ANY, make_bitmap(wx.Bitmap(osp.join(root, 'imgs/stl.png'), wx.BITMAP_TYPE_ANY )), wx.DefaultPosition, wx.DefaultSize, wx.BU_AUTODRAW )
        tsizer.Add( self.btn_stl, 0, wx.ALIGN_CENTER|wx.ALL, 0 )
        #pan = wx.Panel(self.toolbar, size=(50, 50))
        # self.btn_color = wx.ColourPickerCtrl( self.toolbar, wx.ID_ANY, wx.Colour( 255, 255, 255 ), wx.DefaultPosition, [(33, 38), (-1, -1)][platform.system() in ['Windows', 'Linux']], wx.CLRP_DEFAULT_STYLE )
        self.btn_color = wx.ColourPickerCtrl(self.toolbar, wx.ID_ANY, wx.Colour(255, 255, 255, 255), wx.DefaultPosition,
                                             wx.DefaultSize, wx.CLRP_DEFAULT_STYLE)
        tsizer.Add(self.btn_color, 0, wx.ALIGN_CENTER | wx.ALL, 1)

        # tsizer.Add( self.btn_color, 0, wx.ALIGN_CENTER|wx.ALL|(0, wx.EXPAND)[platform.system() in ['Windows', 'Linux']], 0 )
        tsizer.Add(wx.StaticLine( self.toolbar, wx.ID_ANY,  wx.DefaultPosition, wx.DefaultSize, wx.LI_VERTICAL), 0, wx.ALL|wx.EXPAND, 2 )
        self.cho_light = wx.Choice( self.toolbar, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, ['force light', 'normal light', 'weak light', 'off light'], 0 )
        self.cho_light.SetSelection( 1 )
        tsizer.Add( self.cho_light, 0, wx.ALIGN_CENTER|wx.ALL, 1 )
        self.cho_bg = wx.Choice( self.toolbar, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, ['force scatter', 'normal scatter', 'weak scatter', 'off scatter'], 0 )
        self.cho_bg.SetSelection( 1 )
        tsizer.Add( self.cho_bg, 0, wx.ALIGN_CENTER|wx.ALL, 1 )

        self.toolbar.SetSizer( tsizer )
        tsizer.Layout()

        self.settingbar = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        ssizer = wx.BoxSizer( wx.HORIZONTAL )
        
        self.m_staticText1 = wx.StaticText( self.settingbar, wx.ID_ANY, u"Object:", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText1.Wrap( -1 )
        ssizer.Add( self.m_staticText1, 0, wx.ALIGN_CENTER|wx.LEFT, 10 )
        
        cho_objChoices = ['None']
        self.cho_obj = wx.Choice( self.settingbar, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, cho_objChoices, 0 )
        self.cho_obj.SetSelection( 0 )
        ssizer.Add( self.cho_obj, 0, wx.ALIGN_CENTER|wx.ALL, 1 )
        
        self.chk_visible = wx.CheckBox( self.settingbar, wx.ID_ANY, u"visible", wx.DefaultPosition, wx.DefaultSize, 0 )
        ssizer.Add( self.chk_visible, 0, wx.ALIGN_CENTER|wx.LEFT, 10 )
        
        self.col_color = wx.ColourPickerCtrl( self.settingbar, wx.ID_ANY, wx.BLACK, wx.DefaultPosition, wx.DefaultSize, wx.CLRP_DEFAULT_STYLE )
        ssizer.Add( self.col_color, 0, wx.ALIGN_CENTER|wx.ALL, 1 )
        
        self.m_staticText2 = wx.StaticText( self.settingbar, wx.ID_ANY, u"Blend:", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText2.Wrap( -1 )
        ssizer.Add( self.m_staticText2, 0, wx.ALIGN_CENTER|wx.LEFT, 10 )
        
        self.sli_blend = wx.Slider( self.settingbar, wx.ID_ANY, 10, 0, 10, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL )
        ssizer.Add( self.sli_blend, 0, wx.ALIGN_CENTER|wx.ALL, 1 )
        self.settingbar.SetSizer(ssizer)

        self.m_staticText2 = wx.StaticText( self.settingbar, wx.ID_ANY, u"Mode:", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.m_staticText2.Wrap( -1 )
        ssizer.Add( self.m_staticText2, 0, wx.ALIGN_CENTER|wx.LEFT, 10 )

        cho_objChoices = ['mesh', 'grid']
        self.cho_mode = wx.Choice( self.settingbar, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, cho_objChoices, 0 )
        self.cho_mode.SetSelection( 0 )
        ssizer.Add( self.cho_mode, 0, wx.ALIGN_CENTER|wx.ALL, 1 )

        sizer.Add( self.toolbar, 0, wx.EXPAND |wx.ALL, 0 )
        sizer.Add( self.canvas, 1, wx.EXPAND |wx.ALL, 0)
        sizer.Add( self.settingbar, 0, wx.EXPAND |wx.ALL, 0 )
        
        self.SetSizer( sizer )
        self.Layout()
        self.Centre( wx.BOTH )
        
        self.btn_x.Bind( wx.EVT_BUTTON, self.view_x)
        self.btn_y.Bind( wx.EVT_BUTTON, self.view_y)
        self.btn_z.Bind( wx.EVT_BUTTON, self.view_z)
        self.btn_open.Bind( wx.EVT_BUTTON, self.on_open)
        self.btn_stl.Bind( wx.EVT_BUTTON, self.on_stl)
        self.btn_pers.Bind( wx.EVT_BUTTON, lambda evt, f=self.on_pers:f(True))
        self.btn_orth.Bind( wx.EVT_BUTTON, lambda evt, f=self.on_pers:f(False))
        self.btn_color.Bind( wx.EVT_COLOURPICKER_CHANGED, self.on_bgcolor )

        self.cho_obj.Bind( wx.EVT_CHOICE, self.on_select )
        self.cho_mode.Bind( wx.EVT_CHOICE, self.on_mode )
        self.cho_light.Bind( wx.EVT_CHOICE, self.on_light )
        self.cho_bg.Bind( wx.EVT_CHOICE, self.on_bg )
        self.chk_visible.Bind( wx.EVT_CHECKBOX, self.on_visible)
        self.sli_blend.Bind( wx.EVT_SCROLL, self.on_blend )
        self.col_color.Bind( wx.EVT_COLOURPICKER_CHANGED, self.on_color )

        if manager!=None: self.cho_obj.Set(list(manager.objs.keys()))
        pub.subscribe(self.add_surf, 'add_surf')
        pub.subscribe(self.add_mark, 'add_mark')

    def view_x(self, evt): 
        self.canvas.manager.reset(angx=0)
        self.canvas.Refresh(False)


    def view_y(self, evt): 
        self.canvas.manager.reset(angx=pi/2)
        self.canvas.Refresh(False)

    def view_z(self, evt): 
        self.canvas.manager.reset(angy=pi/2-1e-4)
        self.canvas.Refresh(False)

    def on_pers(self, b):
        self.canvas.manager.set_pers(pers=b)
        self.canvas.Refresh(False)

    def on_bgcolor(self, event):
        c = tuple(np.array(event.GetColour()[:3])/255)
        self.canvas.manager.set_background(c)
        self.canvas.Refresh(False)

    def on_bg(self, event):
        scatter = 3 - self.cho_bg.GetSelection()
        self.canvas.manager.set_bright_scatter(scatter=scatter/3)
        self.canvas.Refresh(False)

    def on_light(self, event):
        bright = 3 - self.cho_light.GetSelection()
        self.canvas.manager.set_bright_scatter(bright=bright/3)
        self.canvas.Refresh(False)

    def on_save(self, evt):
        dic = {'open':wx.FD_OPEN, 'save':wx.FD_SAVE}
        filt = 'PNG files (*.png)|*.png'
        dialog = wx.FileDialog(self, 'Save Picture', '', '', filt, wx.FD_SAVE)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.canvas.save_bitmap(path)
        dialog.Destroy()

    def on_stl(self, evt):
        filt = 'STL files (*.stl)|*.stl'
        dialog = wx.FileDialog(self, 'Save STL', '', '', filt, wx.FD_SAVE)
        rst = dialog.ShowModal()
        if rst == wx.ID_OK:
            path = dialog.GetPath()
            self.canvas.save_stl(path)
        dialog.Destroy()

    def on_open(self, evt):
        from stl import mesh
        filt = 'STL files (*.stl)|*.stl'
        dialog = wx.FileDialog(self, 'Open STL', '', '', filt, wx.FD_OPEN)
        rst = dialog.ShowModal()
        if rst == wx.ID_OK:
            path = dialog.GetPath()
            cube = mesh.Mesh.from_file(path)
            verts = cube.vectors.reshape((-1,3)).astype(np.float32)
            ids = np.arange(len(verts), dtype=np.uint32).reshape((-1,3))
            norms = count_ns(verts, ids)
            fp, fn = osp.split(path)
            fn, fe = osp.splitext(fn)
            self.add_surf_asyn(fn, verts, ids, norms, (1,1,1))
        dialog.Destroy()

    def get_obj(self, name):
        return self.canvas.manager.get_obj(name)

    def on_visible(self, evt):
        self.curobj.set_style(visible=evt.IsChecked())
        self.canvas.Refresh(False)

    def on_blend(self, evt):
        self.curobj.set_style(blend=evt.GetInt()/10.0)
        self.canvas.Refresh(False)

    def on_mode(self, evt):
        self.curobj.set_style(mode=evt.GetString())
        self.canvas.Refresh(False)

    def on_color(self, evt):
        c = tuple(np.array(evt.GetColour()[:3])/255)
        self.curobj.set_style(color = c)
        self.canvas.Refresh(False)

    def on_select(self, evt):
        n = self.cho_obj.GetSelection()
        self.curobj = self.get_obj(self.cho_obj.GetString(n))
        self.chk_visible.SetValue(self.curobj.visible)
        color = (np.array(self.curobj.color)*255).astype(np.uint8)
        self.col_color.SetColour((tuple(color)))
        self.sli_blend.SetValue(int(self.curobj.blend*10))
        self.cho_mode.SetSelection(['mesh', 'grid'].index(self.curobj.mode))

    def add_surf_asyn(self, name, vts, fs, ns, cs, mode=None, blend=None, color=None, visible=None):
        wx.CallAfter(pub.sendMessage, 'add_surf', name=name, vts=vts, fs=fs, ns=ns, cs=cs, obj=self,
            mode=mode, blend=blend, color=color, visible=visible)

    def add_surf(self, name, vts, fs, ns, cs, obj=None, mode=None, blend=None, color=None, visible=None):
        if obj!=None and not obj is self:return
        manager = self.canvas.manager
        surf = manager.add_surf(name, vts, fs, ns, cs)

        surf.set_style(mode=mode, blend=blend, color=color, visible=visible)
        if len(manager.objs)==1:
            manager.reset()
        self.cho_obj.Append(name)
        self.canvas.Refresh(False)

    def add_mark_asyn(self, name, vts, fs, ps, h, cs):
        wx.CallAfter(pub.sendMessage, 'add_mark', name=name, vts=vts, fs=fs, ps=ps, h=h, cs=cs)

    def add_mark(self, name, vts, fs, ps, h, cs):
        manager = self.canvas.manager
        surf = manager.add_mark(name, vts, fs, ps, h, cs)
        if len(manager.objs)==1:
            manager.reset()
        self.cho_obj.Append(name)
        self.canvas.Refresh(False)

if __name__ == '__main__':
    app = wx.App(False)
    frm = wx.Frame(None, title='GLCanvas Sample')
    canvas = Canvas3D(frm)

    frm.Show()
    app.MainLoop()