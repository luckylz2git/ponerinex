import kivy
# Ponerine.X Multi-Cam Controller for XueTan
kivy.require('1.9.0')

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import Screen, ScreenManager , SlideTransition
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.spinner import Spinner

from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.factory import Factory
from kivy.lang import Builder, Parser, ParserException
from kivy.uix.popup import Popup
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ObjectProperty

# Camera Object[camera.py]
from xcamera import XCamera
from xcameratelnet import XCameraTelnet
'''
platform.system()
"Windows", "Darwin", "Linux"
'''
import json, os, threading, time, socket, platform, inspect, string
from os.path import basename

Builder.load_file('xdata/xconnectscreen.kv')
Builder.load_file('xdata/xpopupconfig.kv')

Clock.max_iteration = 100
__version__='0.0.1'

class XConnectScreen(Screen):
  pass

class AdvancedPopup(Popup):
  scenename = StringProperty()
  scenecount = NumericProperty()
  autorename = BooleanProperty()
  buzzeronstart = BooleanProperty()
  buzzeronstop = BooleanProperty()
  buzzermute = BooleanProperty()
  loadallsettings = BooleanProperty()
  apply = BooleanProperty()

class ConfigPopup(Popup):
  cfg = ObjectProperty()
  apply = BooleanProperty()
  
class XPonerine(ScreenManager):
  def __init__(self, appevent):
    super(XPonerine, self).__init__()

    self.applyconfig = False
    self.appexit = appevent[0]
    #self.apppause = appevent[1]
    #self.appresume = appevent[2]
    self.inited = False
    self.textcaminfo = ""  # Camera Information
    self.timecontitle = time.time() # Connect Title
    self.textctrlbtn = ""  # Control Buttons
    self.cfglist = []
    self.autorename = False
    self.buzzeronstart = False
    self.buzzeronstop = False
    self.buzzermute = False
    self.scenename = "scene"
    self.scenecount = 1
    self.cfglist = self.ReadConfig()
    self.stopdetect = threading.Event()
    self.resizecam = threading.Event()
    self.connect = threading.Event()
    self.recordstart = threading.Event()
    self.recordstop = threading.Event()
    
    sysname = platform.system()
    if sysname == "Windows":
      Window.size = (560,800) #(1200,800)
      #Window.borderless = '1'
    elif sysname == "Darwin":
      Window.size = (520,700)
    elif sysname == "Linux":
      if platform.linux_distribution()[0] == "Ubuntu":
        Window.size = (560,800)
        
  def InitialCamIcon(self):
    for child in self.current_screen.children[0].children[:]:
      # title
      if isinstance(child, BoxLayout):
        self.btncamsetup = child.children[0]
      # camera icons
      elif isinstance(child, GridLayout):
        pass
      # control or recordtime
      elif isinstance(child, AnchorLayout):
        i = 0
        for btn in child.children[0].children[:]:
          if isinstance(btn, Button):
            i += 1
        # control
        if i == 3:
          self.btnpreview = child.children[0].children[0]
          self.btnrecord = child.children[0].children[1]
          self.btnrecord.text = "%s-%02d" %(self.scenename,self.scenecount)
          self.btnbuzzer = child.children[0].children[2]
        # record time
        else:
          self.lblrecordtime = child.children[0].children[1]
          self.btnrecordtime = child.children[0].children[2]
    return
    self.lblcamname = []
    self.lblcamstatus = []
    self.btnconctrl = []
    self.btnconctrl.append({"color":"0,0,0,1",
                         "disabled_color":"0,0,0,0.5",
                         "disabled":"False",
                         "text":"CONNECT",
                         "background_normal":"image/mcamera_normal.png",
                         "background_down":"image/mcamera_down.png",
                         "background_disabled_normal":"image/mcamera_noip.png",
                         "background_disabled_down":"image/mcamera_noip.png"})
    self.btnconctrl.append({"color":"0,0,0,1",
                         "disabled_color":"0,0,0,0.5",
                         "disabled":"True",
                         "text":"RECORD",
                         "background_normal":"image/mcamera_normal.png",
                         "background_down":"image/mcamera_down.png",
                         "background_disabled_normal":"image/mcamera_noip.png",
                         "background_disabled_down":"image/mcamera_noip.png"})
    self.btnconctrl.append({"color":"0,0,0,1",
                         "disabled_color":"0,0,0,0.5",
                         "disabled":"True",
                         "text":"BUZZER",
                         "background_normal":"image/mcamera_normal.png",
                         "background_down":"image/mcamera_down.png",
                         "background_disabled_normal":"image/mcamera_noip.png",
                         "background_disabled_down":"image/mcamera_noip.png"})
    #self.recordtime = ""
    #self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
    
    for i in range(self.cameras):      
      if self.cfglist[i]["ip"] <> "" and self.cfglist[i]["enabled"] == 1:
        if self.cfglist[i]["name"] == "":
          self.current_screen.ids['lblCamName%d' %i].text = "[b][sup]%s[/sup][/b] CAM" %(self.cfglist[i]["camera"])
        else:
          self.current_screen.ids['lblCamName%d' %i].text = "[b][sup]%s[/sup][/b] %s" %(self.cfglist[i]["camera"],self.cfglist[i]["name"])
        self.lblcamname.append(self.current_screen.ids['lblCamName%d' %i].text)
        self.current_screen.ids['lblCamStatus%d' %i].text = "[color=000000]searching[/color]"
        self.lblcamstatus.append("[color=000000]searching[/color]")
        threading.Thread(target=self.DoDetectCam, name="DoDetectCam%d" %i,
                         args=(i, self.cfglist[i]["ip"], 1,)).start()
      else:
        self.current_screen.ids['lblCamName%d' %i].text = ""
        self.lblcamname.append("")
        self.current_screen.ids['lblCamStatus%d' %i].text = ""
        self.lblcamstatus.append("")
    self.inited = True
    t = threading.Thread(target=self.DoRefreshConnectControl, name="DoRefreshConnectControl")
    t.setDaemon(True)
    t.start()
        
  def DetectCam(self, timewait = 1):
    for thread in threading.enumerate():
      if thread.isAlive() and thread.name[0:11] == "DoDetectCam":
        print "main.py.DoDetectCam kill: %s" %thread.name
        try:
          thread._Thread__stop()
        except:
          pass
  
    self.RefreshCameraInformation(0.5)
    
    self.btnbuzzer.disabled = False
    self.btnbuzzer.text = "CONNECT"
    self.btnbuzzer.background_normal = 'image/mcamera_normal.png'
    self.btnbuzzer.color = (0,0,0,1)
    self.btnconctrl[0]["disabled"] = "False"
    self.btnconctrl[0]["text"] = "CONNECT"
    self.btnconctrl[0]["background_normal"] = "image/mcamera_normal.png"
    self.btnconctrl[0]["color"] = "0,0,0,1"
    
    self.btnrecord.disabled = True
    self.btnrecord.text = "RECORD"
    self.btnrecord.background_disabled_normal = 'image/mcamera_noip.png'
    self.btnrecord.disabled_color = (0,0,0,0.5)
    self.btnconctrl[1]["disabled"] = "True"
    self.btnconctrl[1]["text"] = "RECORD"
    self.btnconctrl[1]["background_disabled_normal"] = "image/mcamera_noip.png"
    self.btnconctrl[1]["disabled_color"] = "0,0,0,0.5"
    
    self.btnpreview.disabled = True
    self.btnpreview.text = "BUZZER"
    self.btnpreview.background_disabled_normal = 'image/mcamera_noip.png'
    self.btnpreview.disabled_color = (0,0,0,0.5)
    self.btnconctrl[2]["disabled"] = "True"
    self.btnconctrl[2]["text"] = "BUZZER"
    self.btnconctrl[2]["background_disabled_normal"] = "image/mcamera_noip.png"
    self.btnconctrl[2]["disabled_color"] = "0,0,0,0.5"
    
    #*#self.RefreshConnectControl()
    
    for i in range(self.cameras):
      if self.cfglist[i]["ip"] <> "" and self.cfglist[i]["enabled"] == 1:
        self.lblcamstatus[i] = "[color=000000]searching[/color]"
        threading.Thread(target=self.DoDetectCam, name="DoDetectCam%d" %i,
                       args=(i, self.cfglist[i]["ip"], 1,)).start()
      else:
        self.lblcamstatus[i] = ""

  def DoDetectCam(self, index, ip, timewait = 1):
    port = [7878, 8787, 554, 23]
    if ip == "":
      return
    self.appexit.wait(timewait)
    timewait = 0
    print "start DoDetectCam %d" %index
    socket.setdefaulttimeout(5)
    retry = 0
    while not self.appexit.isSet():
      #print timewait
      if timewait > 0:    
        self.stopdetect.wait(timewait)
      if self.stopdetect.isSet():
        return 
      retry = (retry + 1) % len(port)
      #index = index % 2
      srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      srv.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
      print "port", port[retry]
      open = srv.connect_ex((ip, port[retry])) #7878
      srv.close()
      print "Detect Cam IP %s Index %d state %d retry %d" %(ip, index, open, retry)
      if self.stopdetect.isSet():
        return
      if open == 0:
        self.lblcamstatus[index] = "[color=0000ff]online[/color]"
        self.RefreshCameraInformation(0.5)
        return
      elif retry == 0:
        if timewait < 10:
          timewait += 1
        self.lblcamstatus[index] = "[color=ff0000]off line[/color]"
        self.RefreshCameraInformation(2)
  
  def Connect(self, btnbuzzer):
    #kv_container = self.current_screen.children[0]
    #kv_widget = kv_container.children[0]
    #kv_container.remove_widget(kv_widget)
#     self.lblcamname = ["[b]CAM [sup]1[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]2[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]3[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]4[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]5[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]6[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]7[/sup][/b] [sub]camera1[/sub]",
#                      "[b]CAM [sup]8[/sup][/b] [sub]camera1[/sub]"]
#     self.lblcamstatus = ["[color=ff0000]record[/color]",
#                        "[color=00ff00]record[/color]",
#                        "[color=0000ff]record[/color]",
#                        "[color=000000]record[/color]",
#                        "[color=ffff00]record[/color]",
#                        "[color=ff00ff]record[/color]",
#                        "[color=00ffff]record[/color]",
#                        "[color=ffffff]record[/color]"]
#     Clock.unschedule(self.BuildCameraInformation)
#     Clock.schedule_once(self.BuildCameraInformation)
#     return
    if btnbuzzer.text == "CONNECT":
      btnbuzzer.disabled = True
      self.btnconctrl[0]["disabled"] = "True"
      self.btncamsetup.disabled = True
      #self.setupdisabled = "True"
      self.stopdetect.set()
      self.connect.clear()
      self.recordstart.clear()
      self.recordstop.clear()
      self.cam = []
      idx = 0
      num = 0
      self.linked = 0
      self.error = 0
      self.retry = []
      self.firstcam = 0
      self.synctime = time.strftime('%Y-%m-%d %H:%M:')
      for cfg in self.cfglist:
        if cfg["enabled"] == 1 and cfg["ip"] <> "":
          self.cam.append(XCamera(ip=cfg["ip"],preview=cfg["preview"]==1))
          threading.Thread(target=self.DoConnect, args=(idx,num,), name="DoConnect%d" %idx).start()
          idx += 1
        num += 1
      self.connect.set()
      threading.Thread(target=self.DoShowConnect, args=(0,), name="DoShowConnect").start()
    elif btnbuzzer.text == "RETRY": # Retry connect to rest of the camera
      btnbuzzer.disabled = True
      self.btncamsetup.disabled = True
      #self.setupdisabled = "True"
      self.connect.clear()
      self.error = 0
      for itm in self.retry:
        idx = itm["index"]
        num = itm["number"]
        self.cam[idx].quit.clear()
        threading.Thread(target=self.DoConnect, args=(idx,num,), name="DoConnect%d" %idx).start()
      self.retry = []
      self.connect.set()
      threading.Thread(target=self.DoShowConnect, args=(2,), name="DoShowConnect").start()
    elif btnbuzzer.text == "DISCONNECT":
      btnbuzzer.disabled = True
      self.btnconctrl[0]["disabled"] = "True"
      self.btnrecord.disabled = True
      self.btnconctrl[1]["disabled"] = "True"
      self.btnpreview.disabled = True
      self.btnconctrl[2]["disabled"] = "True"
      threading.Thread(target=self.DoDisconnect, name="DoDisconnect").start()
      self.connect.set()
      threading.Thread(target=self.DoShowConnect, args=(1,), name="DoShowConnect").start()
    #*#self.RefreshConnectControl()
    
  def DoShowConnect(self, type):
    i = 0
    #self.btnbuzzer.background_disabled_normal = 'image/mcamera_normal.png'
    #self.btnbuzzer.disabled = True
    while self.connect.isSet():
      if i == 0:
        i = 1
        self.btnbuzzer.background_disabled_normal = 'image/mcamera_linked.png'
        self.btnconctrl[0]["background_disabled_normal"] = "image/mcamera_linked.png"
      else:
        i = 0
        if type in (0,2): #connect & retry
          self.btnbuzzer.background_disabled_normal = 'image/mcamera_connect.png'
          self.btnconctrl[0]["background_disabled_normal"] = "image/mcamera_connect.png"
          if self.linked == len(self.cam):
            self.connect.clear()
            self.btnrecord.disabled = False
            self.btnconctrl[1]["disabled"] = "False"
            self.btnpreview.disabled = False
            self.btnconctrl[2]["disabled"] = "False"
            # Preview On/Off
            threading.Thread(target=self.DoPreview, name="DoThrPreview").start()
            i = 0
            for cfg in self.cfglist:
              if cfg["enabled"] == 1 and cfg["ip"] <> "":
                self.lblcamstatus[i] = '[color=00cc00]ready[/color]'
              i += 1
            self.btnbuzzer.disabled = False
            self.btnbuzzer.color = (0,0,0,1)
            self.btnconctrl[0]["disabled"] = "False"
            self.btnconctrl[0]["color"] = "0,0,0,1"
            self.btnconctrl[0]["text"] = "DISCONNECT"
            self.RefreshConnectControl(1)
            break
          elif (self.linked + self.error) == len(self.cam):
            self.connect.clear()
            if type == 0:
              self.btnbuzzer.disabled = False
              self.btnbuzzer.color = (1,0,0,1)
              self.btnbuzzer.text = "ERR %d / %d" %(self.error, len(self.cam))
              self.btnconctrl[0]["disabled"] = "False"
              self.btnconctrl[0]["text"] = "ERR %d / %d" %(self.error, len(self.cam))
              self.btnconctrl[0]["color"] = "1,0,0,1"
              self.btnconctrl[0]["text"] = "RETRY"
              self.RefreshConnectControl(1)
              #threading.Thread(target=self.ButtonText, args=(self.btnbuzzer,"RETRY",1,), name="ButtonText").start()
              break
            else: #retry
              self.btnbuzzer.text = "ERR %d / %d" %(self.error, len(self.cam))
              time.sleep(1.5)
              self.btnbuzzer.text = "DISCONNECT"
              self.btnconctrl[0]["text"] = "DISCONNECT"
              threading.Thread(target=self.Connect, args=(self.btnbuzzer,),name="Disconnect").start()
              break
        else: #disconnect
          #self.btnconctrl[0]["text"] = "DISCONNECT"
          self.btnbuzzer.background_disabled_normal = 'image/mcamera_disconnect.png'
          self.btnconctrl[0]["background_disabled_normal"] = "image/mcamera_disconnect.png"
#       self.btnbuzzer.texture_update()
#       self.btnpreview.texture_update()
#       self.btnrecord.texture_update()
      self.RefreshCameraInformation(1)
      #*#self.RefreshConnectControl()
      time.sleep(1)
    self.RefreshCameraInformation(1)
    
    #*#self.RefreshConnectControl()
    
  def DoConnect(self, index, number):
    self.connect.wait()
    
    cam = self.cam[index]
    #btn = self.btncamsetup[number]
    quit = cam.quit
    cam.LinkCamera()
    while True:
      if cam.link:
        break
      quit.wait(1)
      if quit.isSet():
        self.error += 1
        self.retry.append(json.loads('{"index":%d,"number":%d}' %(index,number)))
        self.lblcamstatus[number] = '[color=ff0000]fail to connect[/color]'
        print "Fail to connect camera %d" %number
        return
    self.linked += 1
    self.lblcamstatus[number] = '[color=00cc00]ready[/color]'
    self.btnbuzzer.text = 'CAM %d / %d' %(self.linked, len(self.cam))
    self.btnconctrl[0]["text"] = 'CAM %d / %d' %(self.linked, len(self.cam))
    # Listen Start Record Command
    threading.Thread(target=self.DoStartRecord, args=(index,number,), name="DoThrStartRecord%d" %index).start()
    threading.Thread(target=self.DoWifi, args=(index,), name="DoThrWifi%d" %index).start()
    threading.Thread(target=self.DoFileTaken, args=(index,number,), name="DoThrFileTaken%d" %index).start()
    
  def DoDisconnect(self, timewait = 1):
    try:
      for cam in self.cam:
        if cam.link:
          if self.buzzermute and cam.volume <> "mute":
            setok = cam.setok
            cam.ChangeSetting("buzzer_volume",cam.volume)
            setok.wait(5)
            cam.msgbusy = 0
          time.sleep(1)
          cam.UnlinkCamera()
          cam.quit.wait(5)
    except:
      pass
    self.connect.clear()
    self.stopdetect.clear()
    for thread in threading.enumerate():
      if thread.isAlive() and thread.name[0:5] == "DoThr":
        print "main.py.DoDisconnect kill: %s" %thread.name
        try:
          thread._Thread__stop()
        except:
          pass
    self.btncamsetup.disabled = False
    #self.setupdisabled = "False"
    time.sleep(1.5)
    self.DetectCam(timewait)
    
  def DoStartRecord(self, index, number):
    cam = self.cam[index]
    retry = False
    while True:
      self.recordstart.wait()
      cam.StartRecord(False)
      cam.recording.wait(10)
      if cam.recording.isSet():
        retry = False
        print "\nDoStartRecord", index
        if self.linked == 0:
          self.firstcam = index
          print "self.firstcam", self.firstcam
        self.linked += 1
        self.btnrecord.text = 'CAM %d / %d' %(self.linked, len(self.cam))
        self.btnconctrl[1]["text"] = 'CAM %d / %d' %(self.linked, len(self.cam))
        self.lblcamstatus[number] = "[color=ff0000]recording[/color]"
        threading.Thread(target=self.DoStopRecord, args=(index,number,), name="DoStopRecord%d" %index).start()
        if self.linked == len(self.cam):
          self.trec = time.time()
          if self.buzzeronstart:
            #threading.Thread(target=self.DoBuzzerRing, args=(3,), name="DoBuzzerRing").start()
            threading.Thread(target=self.DoBuzzerRing, name="DoBuzzerRing").start()
          self.btnconctrl[1]["text"] = "STOP"
          self.RefreshConnectControl(1)
          #threading.Thread(target=self.ButtonText, args=(self.btnrecord,"STOP",1,), name="ButtonText").start()
          threading.Thread(target=self.DoShowRecord, name="DoShowRecord").start()
          threading.Thread(target=self.DoShowTime, name="DoShowTime").start()
          self.recordstart.clear()
          self.btnrecord.disabled = False
          self.btnconctrl[1]["disabled"] = "False"
          self.recordtime = self.Second2Time(time.time() - self.trec)
          self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
          
        if cam.preview:
          cam.StartViewfinder()
        self.RefreshCameraInformation(1)
        #*#self.RefreshConnectControl(1)
        self.recordstop.wait()
      elif retry:
        retry = False
        self.recordstart.clear()
        self.btnrecord.disabled_color = (1,0,0,1)
        self.btnrecord.text = "ERROR"
        time.sleep(2)
        self.btnrecord.disabled_color = (0,0,0,1)
        self.btnrecord.text == "STOP"
        self.btnconctrl[1]["disabled_color"] = "0,0,0,1"
        self.btnconctrl[1]["text"] = "STOP"
        #*#self.RefreshConnectControl(1)
        self.Record(self.btnrecord) #STOP
        self.recordstop.wait()
      else:
        retry = True
        
  def DoShowTime(self):
    txtold = self.Second2Time(time.time() - self.trec)
    txtnew = txtold
    while True:
      txtnew = self.Second2Time(time.time() - self.trec)
      if txtnew <> txtold:
        self.recordtime = txtnew
        self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
        txtold = txtnew
      if self.btnrecord.text == "STOP":
        break
    while True:
      txtnew = self.Second2Time(time.time() - self.trec)
      if txtnew <> txtold:
        self.recordtime = txtnew
        self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
        txtold = txtnew
      if self.btnrecord.text <> "STOP":
        break
    
  def DoShowRecord(self):
    i = 0
    while True:
      if self.btnrecord.text == "STOP":
        if i == 0:
          i = 1
          self.btnrecord.background_normal = 'image/mcamera_disconnect.png'
          self.btnconctrl[1]["background_normal"] = "image/mcamera_disconnect.png"
        else:
          i = 0
          self.btnrecord.background_normal = 'image/mcamera_normal.png'
          self.btnconctrl[1]["background_normal"] = "image/mcamera_normal.png"
        
        #print self.btnrecord.text, self.btnrecord.background_normal, i
      self.recordstop.wait(1)
      if self.recordstop.isSet() or self.btnrecord.text in ("RECORD", "STOPPING", "ERROR"):
        self.btnrecord.background_normal = 'image/mcamera_normal.png'
        self.btnconctrl[1]["background_normal"] = "image/mcamera_normal.png"
        #*#self.RefreshConnectControl(1)
        return
      #*#self.RefreshConnectControl(1)
    
  def DoStopRecord(self, index, number):
    self.recordstop.wait()
    cam = self.cam[index]
    cam.taken.clear()
    if cam.recording.isSet():
      #if self.buzzeronstop:
      #  cam.msgbusy = 0
      cam.StopRecord()
    print "DoStopRecord", index
    print cam.filetaken
    stopfirst = self.linked
    self.linked += 1
    if stopfirst == 0: #show last record time
      self.firstcam = index
      self.recordtime = self.Second2Time(time.time() - self.trec)
      self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
    self.btnrecord.text = 'CAM %d / %d' %(self.linked, len(self.cam))
    self.btnconctrl[1]["text"] = 'CAM %d / %d' %(self.linked, len(self.cam))
    self.lblcamstatus[number] = "[color=0000ff]stop record[/color]"
    self.RefreshCameraInformation(1)
    if self.linked == len(self.cam):
      self.btnconctrl[1]["text"] = "RECORD"
      self.btnrecord.text = "RECORD"
      #threading.Thread(target=self.ButtonText, args=(self.btnrecord,"RECORD",1.5,), name="ButtonText").start()
      self.recordstop.clear()
      self.btnrecord.background_normal = 'image/mcamera_normal.png'
      self.btnrecord.disabled = False
      self.btnconctrl[1]["background_normal"] = 'image/mcamera_normal.png'
      self.btnconctrl[1]["disabled"] = 'False'
    #*#self.RefreshConnectControl(1)
    
  def Buzzer(self, btnbuzzer):
    threading.Thread(target=self.DoBuzzerRing, args = (True,),name="DoBuzzerRing").start()
    
  def DoBuzzerRing(self, force=False):
    print "self.firstcam",self.firstcam
    cam = self.cam[self.firstcam]
    if force == False:
      while True:
        if cam.vfstart == False:
          break
      cam.SendMsg('{"msg_id":515}')
      rtime = cam.recordtime
      while True:
        if cam.recordtime <> rtime:
          rtime = cam.recordtime
          print "first rtime", rtime
          break
        else:
          time.sleep(1)
          cam.SendMsg('{"msg_id":515}')

    setok = cam.setok
    seterror = cam.seterror

    cam.ChangeSetting("buzzer_ring","on")
    if force:
      t = time.time()
      setok.wait(5)
      if setok.isSet():
        if time.time() - t < 3.0:
          time.sleep(2)
        #cam.SendMsg('{"msg_id":1,"type":"app_status"}')
    else:
      rtime = cam.recordtime
      print "second rtime", rtime
      cam.SendMsg('{"msg_id":515}')
      while True:
        if int(cam.recordtime.split(':')[2]) - 2 >= int(rtime.split(':')[2]):
          break
        else:
          time.sleep(1)
          cam.SendMsg('{"msg_id":515}')
    cam.ChangeSetting("buzzer_ring","off")
    #cam.msgbusy = 0
            
  def ButtonBackground(self, button, type, imagefilepath):
    if type == "background_normal":
      button.background_normal = imagefilepath
    elif type == "background_down":
      button.background_down = imagefilepath
    elif type == "background_disabled_normal":
      button.background_disabled_normal = imagefilepath
    elif type == "background_disabled_down":
      button.background_disabled_normal = imagefilepath
  
  def Record(self, btnrecord):
    if btnrecord.text == "RECORD":
      self.linked = 0
      self.rename = 0
      self.renlist = []
      self.firstcam = 0
      self.recordstop.clear()
      self.recordstart.set()
      btnrecord.text == "STARTING"
      btnrecord.disabled = True
      self.btnconctrl[1]["text"] = 'STARTING'
    elif btnrecord.text == "STOP":
      self.linked = 0
      self.rename = 0
      self.renlist = []
      btnrecord.text == "STOPPING"
      btnrecord.disabled = True
      self.btnconctrl[1]["text"] = 'STOPPING'
      if self.buzzeronstop:
        self.DoBuzzerRing()
      self.recordstart.clear()
      self.recordstop.set()
    self.btnconctrl[1]["disabled"] = 'True'
    #*#self.RefreshConnectControl()

#   def AdvancedPopupOpen(self):
#     print type(self.parent)
#     print "Connection Config - Camera Count"
#     self.stopdetect.set()
#     self.advancedpopup = AdvancedPopup(title='Camera Advanced Config', size_hint=(0.8, 0.4), size=self.size)
#     self.advancedpopup.bind(on_dismiss=self.AdvancedPopupApply)
#     self.advancedpopup.apply = False
#     self.advancedpopup.buzzeronstart = self.buzzeronstart
#     self.advancedpopup.buzzeronstop = self.buzzeronstop
#     self.advancedpopup.buzzermute = self.buzzermute
#     self.advancedpopup.open()
    
  def ConfigPopupOpen(self, btnsetup, text):
    if btnsetup.text <> "For XiaoYi Sports Camera":
      text = btnsetup.text
      btnsetup.text = "For XiaoYi Sports Camera"
      if text == "Advanced":
        popup = AdvancedPopup(title='Camera Advanced Config', size_hint=(0.8, 0.7), size=self.size)
        popup.bind(on_dismiss=self.AdvancedPopupApply)
        popup.apply = False
        popup.scenename = self.scenename
        popup.scenecount = self.scenecount
        popup.autorename = self.autorename
        popup.buzzeronstart = self.buzzeronstart
        popup.buzzeronstop = self.buzzeronstop
        popup.buzzermute = self.buzzermute
        popup.loadallsettings = self.loadallsettings
        popup.open()
      else:
        index = int(text.split(" ")[1]) - 1
        self.stopdetect.set()
        popup = ConfigPopup(title='Camera Connection Config', size_hint=(0.8, 0.6), size=self.size, cfg=self.cfglist[index], index=index)
        popup.bind(on_dismiss=self.ConfigPopupApply)
        popup.apply = False
        popup.index = index
        #print self.configpop.apply, self.configpop.index, self.configpop.cfg
        popup.open()
  
  def ConfigPopupApply(self, popup):
    if popup.apply:
      print "index %d ip %s" %(popup.index,popup.cfg)
      self.cfglist[popup.index] = popup.cfg
      self.WriteConfig()
      self.cfglist = self.ReadConfig()
      self.stopdetect.clear()
      self.DetectCam()
      self.RefreshConnectTitle()
  
  def StringFilter(self, strin):
    filter = list(string.ascii_letters + string.digits)
    strout = ""
    for i in range(len(strin)):
      if strin[i] in filter:
        strout += strin[i]
    if strout == "":
      strout = "scene"
    return strout[0:20]
    
  def AdvancedPopupApply(self, popup):
    if popup.apply:
      # Different Scene Name Reset Counter
      if self.scenename <> self.StringFilter(popup.scenename):
        self.scenename = self.StringFilter(popup.scenename)
        #self.lblscenename.text = self.scenename
        self.scenecount = 1
        #self.lblscenecount.text = "No.%d" %self.scenecount
      self.autorename = popup.autorename
      self.buzzeronstart = popup.buzzeronstart
      self.buzzeronstop = popup.buzzeronstop
      self.buzzermute = popup.buzzermute
      self.loadallsettings = popup.loadallsettings
      self.WriteConfig()
      self.RefreshConnectControl()
      
  def Photo(self):
    self.tphoto= threading.Thread(target=self.DoPhoto)
    self.tphoto.setName('DoPhoto')
    self.tphoto.start()
  
  def Second2Time(self, seconds):
    seconds = int(seconds)
    rectime = "00:00:00"
    ihour = 0
    iminute = 0
    isecond = 0
    if seconds <> 0:
      ihour = seconds / 3600
      seconds = seconds % 3600
      iminute = seconds / 60
      isecond = seconds % 60
      rectime = "%02d:%02d:%02d" %(ihour, iminute, isecond)
    return rectime
    
  def DoPhoto(self):
    i = 0
    #self.current_screen.ids.btnpreview.state = "down"
    self.current_screen.ids.btnpreview.text = "Taking Photo"
    for cam in self.cam:
      cam.TakePhoto()
    for cam in self.cam:
      while cam.cambusy:
        i = i % 3 + 1
        time.sleep(0.5)
        self.current_screen.ids.btnpreview.text = "Taking Photo %s" %("." * i)
    #self.current_screen.ids.btnpreview.state = "normal"
    self.current_screen.ids.btnpreview.text = "Take Photo"
  
  def DoPreview(self):
    for cam in self.cam:
      if cam.link and cam.preview:
        cam.StartViewfinder()
        #time.sleep(1)
        #cam.msgbusy = 0
  
  def DoWifi(self, index):
    print "DoWifi Start %d" %index
    wifioff = self.cam[index].wifioff
    wifioff.wait()
    threading.Thread(target=self.DoDisconnect, args=(45,), name="DoDisconnect%d" %index).start()
    wifioff.clear()
    
  def DoFileTaken(self, index, number):
    cam = self.cam[index]
    time.sleep(1)
    t1 = time.time()
    cam.CheckBatteryState()
    while True:
      if cam.status.has_key("battery"):
          break
      if (time.time() - t1) > 10.0:
        cam.msgbusy = 0
        break
      
    setok = cam.setok
    if self.buzzermute:
      cam.SendMsg('{"type":"buzzer_volume","msg_id":1}')
      t1 = time.time()
      while True:
        if cam.cfgdict.has_key("buzzer_volume"):
          break
        if (time.time() - t1) > 10.0:
          cam.msgbusy = 0
          break
      if cam.cfgdict.has_key("buzzer_volume"):
        #print "cam.volume", cam.cfgdict["buzzer_volume"]
        cam.volume = cam.cfgdict["buzzer_volume"]
        if cam.volume <> "mute":
          # Mute Camera
          cam.ChangeSetting("buzzer_volume","mute")
          setok.wait(10)
          self.msgbusy = 0
      else:
        cam.volume = "low"
    # Sync Camera Time, range of: (0,8,16,24,32,40,48,56)
    t = self.synctime + '%02d' %(number * 8)
    cam.ChangeSetting("camera_clock",t)
    setok.wait(10)
    self.msgbusy = 0
    
    if self.loadallsettings:
      cam.SendMsg('{"type":"video_resolution","msg_id":1}')
      t1 = time.time()
      while True:
        if cam.cfgdict.has_key("video_resolution"):
          break
        if (time.time() - t1) > 10.0:
          cam.msgbusy = 0
          break
      if cam.cfgdict.has_key("video_resolution"):
        self.lblcamstatus[number] = "[color=00cc00]%s[/color]" %cam.cfgdict["video_resolution"]
        
    i = 0
    if cam.status.has_key("battery"):
      self.lblcamstatus[number] = self.AddBatteryInfo(self.lblcamstatus[number], cam.status["battery"], cam.status["adapter_status"])
      
    self.RefreshCameraInformation()
    
    while not cam.quit.isSet():
      i = i % 5 + 1
      cam.taken.wait(1)
      if i >= 5 and cam.status.has_key("battery"):
        self.lblcamstatus[number] = self.AddBatteryInfo(self.lblcamstatus[number], cam.status["battery"], cam.status["adapter_status"])
        self.RefreshCameraInformation(1)
          
      if cam.taken.isSet():
        self.rename += 1
        cam.taken.clear()
        self.recordtime = ""
        self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
        if cam.filetaken <> "":
          #debugtxt += "\nCAM %d : " %(index+1) + self.cam[index].filetaken
          self.lblcamstatus[number] = "[sup][b]%s[/b][/sup] [color=0000ff]%s[/color]" %(cam.dirtaken,cam.filetaken)
          if cam.preview:
            cam.StartViewfinder()
          self.RefreshCameraInformation()
          fileinfo = {"index":index,"number":number,"old":cam.status["video_record_complete"],"new":"","ok":0}
          self.renlist.append(fileinfo)
          if self.autorename:
            threading.Thread(target=self.RenameVideoFiles, args=(index,number,), name="RenameVideoFiles%d" %index).start()
    #print "DoFileTaken stop %d" %index
  
  def RenameVideoFiles(self, index, number):
    cam = self.cam[index]
    date = time.strftime('%Y%m%d')
    camletter = list(string.ascii_lowercase)
    failure = False
    old = cam.status["video_record_complete"]
    cam.SendMsg('{"msg_id":1026,"param":"%s"}' %old.replace('.mp4','.THM')) 
    print "old file name:", old
    new = '/tmp/fuse_d/DCIM/%s/%s-%s-%s-%03d.mp4' %(self.scenename,date,self.scenename,camletter[number],self.scenecount)
    print "new file name:", new
    fileinfo = {}
    for item in self.renlist:
      if item["index"] == index:
        item["new"] = new
        fileinfo = item
        break
    ctelnet = XCameraTelnet(ip=cam.ip,username="")
    commit = ctelnet.commit
    ctelnet.Rename(old, new)
    while True:
      commit.wait(1)
      if commit.isSet():
        arr = new.split('/')
        self.lblcamstatus[number] = "[color=0000ff]%s[/color]" %(arr[len(arr)-1])
        if fileinfo <> {}:
          fileinfo["ok"] = 1
        cam.SendMsg('{"msg_id":1026,"param":"%s"}' %new)
        break
      elif ctelnet.failure:
        failure = failure or ctelnet.failure
        self.lblcamstatus[number] = "[color=ff0000]Rename %s Error[/color]" %self.cam[index].filetaken
        print "Rename Error"
        if fileinfo <> {}:
          fileinfo["ok"] = 0
        break
    cam.status["video_record_complete"] = ""
    cam.dirtaken = ""
    cam.filetaken = ""
    self.RefreshCameraInformation()
    if len(self.renlist) == len(self.cam):
      for item in self.renlist:
        if item["ok"] == 0:
          failure = True
          break
      if not failure:
        self.scenecount += 1
        self.WriteConfig()
        self.lblrecordtime.text = "[color=0000ff]%s - %d[/color]\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
  
  def AddBatteryInfo(self, camstatus, battery, adapter):
    if battery == "":
      return camstatus
    else:
      bat = int(battery)
      # adapter_status
      if adapter == "0":
        str = "B"
      else:
        str = "A"
      if bat > 75: # green
        str = "[color=00cc00]%s%d%%[/color] " %(str, bat)
      elif bat > 50: # blue
        str = "[color=0000ff]%s%d%%[/color] " %(str, bat)
      elif bat > 25: # orange
        str = "[color=ff8800]%s%d%%[/color] " %(str, bat)
      else: # red
        str = "[color=ff0000]%s%d%%[/color] " %(str, bat)
      #print "battery color %s" %str
      arr = camstatus.split("%[/color] ")
      if len(arr) == 1:
        return str + arr[0]
      else:
        return str + arr[1]
    
  def ReadConfig(self):
    self.cameras = 6 #default 6 cameras
    cfgfile = __file__.replace(basename(__file__), "xdata/xcamera.cfg")
    initstr = '''
    {
      "camera": "0",
      "ip": "",
      "enabled": 0,
      "name": "",
      "preview": 0
    }
    '''
    r = []
    try:
      with open(cfgfile) as file:
        readstr = file.read()
        #print "readstr", readstr
        cfg = json.loads(readstr)
      if cfg.has_key("scenename"):
        self.scenename = cfg["scenename"]
      if cfg.has_key("scenecount"):
        self.scenecount = cfg["scenecount"]
      if self.scenecount <= 0:
        self.scenecount = 1
      if cfg.has_key("autorename"):
        self.autorename = cfg["autorename"] == 1
      else:
        self.autorename = False
      if cfg.has_key("buzzeronstart"):
        self.buzzeronstart = cfg["buzzeronstart"] == 1
      else:
        self.buzzeronstart = False
      if cfg.has_key("buzzeronstop"):
        self.buzzeronstop = cfg["buzzeronstop"] == 1
      else:
        self.buzzeronstop = False
      if cfg.has_key("buzzermute"):
        self.buzzermute = cfg["buzzermute"] == 1
      else:
        self.buzzermute = False
      if cfg.has_key("loadallsettings"):
        self.loadallsettings = cfg["loadallsettings"] == 1
      else:
        self.loadallsettings = False
      
      if cfg.has_key("config"):
        for item in cfg["config"]:
          cfginit = json.loads(initstr)
          cfginit.update(item)
          r.append(cfginit)
        print "config read len %d of %d" %(len(r), self.cameras)
        if len(r) < self.cameras:
          for i in range(len(r), self.cameras):
            cfginit = json.loads(initstr)
            cfginit["camera"] = str(i+1)
            r.append(cfginit)
      else:
        for i in range(self.cameras):
          cfginit = json.loads(initstr)
          cfginit["camera"] = str(i+1)
          r.append(cfginit)
    except StandardError:
      for i in range(self.cameras):
        cfginit = json.loads(initstr)
        cfginit["camera"] = str(i+1)
        r.append(cfginit)
      self.scenename = "scene"
      self.scenecount = 1
      self.autorename = False
      self.buzzeronstart = False
      self.buzzeronstop = False
      self.buzzermute = False
      self.loadallsettings = False
      
    if self.inited:
      cname = []
      cstatus = []
      csetup = []
      i = 0
      for item in r:
        if item["ip"] <> "" and item["enabled"] == 1:
          cname.append("[b][sup]%s[/sup][/b] %s" %(item["camera"],item["name"]))
        else:
          cname.append("")
        cstatus.append("")
        i += 1
        csetup.append("Camera %d" %i)
      csetup.append("Advanced")
      self.lblcamname = cname
      self.lblcamstatus = cstatus
      self.btncamsetup.values = csetup
    return r

  def WriteConfig(self):
    cfg = {}
    cfg["scenename"] = self.scenename
    cfg["scenecount"] = self.scenecount
    cfg["autorename"] = int(self.autorename)
    cfg["buzzeronstart"] = int(self.buzzeronstart)
    cfg["buzzeronstop"] = int(self.buzzeronstop)
    cfg["buzzermute"] = int(self.buzzermute)
    cfg["loadallsettings"] = int(self.loadallsettings)
    
    cfg["config"] = self.cfglist
    cfgfile = __file__.replace(basename(__file__), "xdata/xcamera.cfg")
    try:
      with open(cfgfile,'w') as file:
        file.write(json.dumps(cfg, indent=2))
    except StandardError:
      pass
  
  def GetCameraInformation(self):
    shead = '''
#:kivy 1.9.0

GridLayout:
  id: grdCameraInformation
  size_hint: None, None
  size: root.width, root.width/7 #+ root.width/10*2
  #spacing: root.width/12, root.width/25
  spacing: 0, root.width/50
  padding: root.width/12,0,root.width/12,0
  cols: 2
  Label:
    text: ""
    size_hint: None, None
    height: root.width/7 - root.width/50
  Label:
    text: ""
'''

    sdetail = '''
  Label:
    id: lblCamName{index}
    size_hint: None, None
    size: (root.width - root.width/10 - root.width/6)/5*2,root.width/10
    color: (0,0,0,1)
    font_size: root.width/22
    text_size: self.size
    valign: "middle"
    halign: "left"
    text: "{$lblCamName}"
    markup: True
  Label:
    id: lblCamStatus{index}
    size_hint: None, None
    size: (root.width - root.width/10 - root.width/6)/5*3,root.width/10
    color: (0,0,0,1)
    font_size: root.width/30
    text_size: self.size
    valign: "middle"
    halign: "left"
    text: "{$lblCamStatus}"
    markup: True
'''
    for i in range(self.cameras):
      shead += sdetail.replace("{index}",str(i)).replace("{$lblCamName}",self.lblcamname[i]).replace("{$lblCamStatus}",self.lblcamstatus[i])
    #print shead.replace("root.width",str(self.width))
    return shead.replace("root.width",str(self.width))

  def BuildCameraInformation(self, *largs):
    txt = self.GetCameraInformation()
    if txt == self.textcaminfo:
      return
    kv_container = self.current_screen.children[0]
    for child in kv_container.children[:]:
      if isinstance(child, GridLayout):
        kv_widget = child
        break
    try:
      parser = Parser(content=txt)
      kv_container.remove_widget(kv_widget)
      widget = Factory.get(parser.root.name)()
      Builder._apply_rule(widget, parser.root, parser.root)
      kv_container.add_widget(widget)
      self.textcaminfo = txt
    except (SyntaxError, ParserException) as e:
      print "SyntaxError, ParserException", e
    except Exception as e:
      print "Exception", e
      
  def RefreshCameraInformation(self, timewait = 0):
    Clock.unschedule(self.BuildCameraInformation)
    if timewait == 0:
      Clock.schedule_once(self.BuildCameraInformation)
    else:
      Clock.schedule_once(self.BuildCameraInformation, timewait)

  def GetConnectTitle(self):
    sbuild = '''
#:kivy 1.9.0

BoxLayout:
  orientation: 'horizontal'
  canvas:
    Color: 
      rgba: 0.95,0.95,0.95,1
    Rectangle:
      size: self.size
      pos: self.pos
  size_hint: None, None
  size: root.width, root.width/15 + root.width/20
  padding: root.width/40, root.width/40, root.width/20, root.width/40
  spacing: root.width/40
  Button:
    size_hint: None, None
    size: root.width/15, root.width/15
    background_normal: 'ximage/logo.png'
    background_down: 'ximage/logo.png'
  Label:
    text_size: self.size
    size_hint: None, None
    size: root.width-(root.width/15+root.width/15*5+root.width/40*3+root.width/20), root.width/15
    halign: 'left'
    valign: 'middle'
    color: 0,0,0,1
    font_size: root.width/25
    text: '[size=%d]Ponerine.[/size][size=%d][b]X[/b][/size][sub] %s[/sub]' %(root.width/22,root.width/18,app.version)
    markup: True
  Spinner:
    size_hint: None, None
    size: root.width/15*5, root.width/15
    text_size: self.size
    halign: 'right'
    valign: 'middle'
    color: 0,0,1,1
    values: ("Camera 1","Camera 2","Camera 3","Camera 4","Camera 5","Camera 6","Advanced")
    background_normal: 'ximage/setting.png'
    background_down: 'ximage/setting.png'
'''
    return sbuild.replace("root.width",str(self.width)) #.replace("{$disabled}",self.setupdisabled)

  def BuildConnectTitle(self, *largs):
    t1 = time.time()
    if t1 - self.timecontitle < 30.0: #allow update every 30seconds
      return
    txt = self.GetConnectTitle()
    #print txt
    #print "BuildConnectTitle"
    kv_container = self.current_screen.children[0]
    for child in kv_container.children[:]:
      if isinstance(child, BoxLayout):
        kv_widget = child
        break
    try:
      parser = Parser(content=txt)
      kv_container.remove_widget(kv_widget)
      widget = Factory.get(parser.root.name)()
      Builder._apply_rule(widget, parser.root, parser.root)
      for child in widget.children[:]:
        if isinstance(child, Button):
          if isinstance(child, Spinner):
            print "Spinner", child
            child.bind(text=self.ConfigPopupOpen)
            self.btncamsetup = child
          else:
            print "Button", child
            child.bind(on_release=self.RefreshAllControls)
      kv_container.add_widget(widget)
      #self.current_screen.ids['btnCamSetup'].bind(text=self.ConfigPopupOpen) #.btnCamSetup.text #bind(on_text=self.ConfigPopupOpen)
      self.timecontitle = t1
    except (SyntaxError, ParserException) as e:
      print "BuildConnectTitle: SyntaxError, ParserException", e
    except Exception as e:
      print "BuildConnectTitle: Exception", e

  def RefreshConnectTitle(self, timewait = 0):
    Clock.unschedule(self.BuildConnectTitle)
    if timewait == 0:
      Clock.schedule_once(self.BuildConnectTitle)
    else:
      Clock.schedule_once(self.BuildConnectTitle, timewait)
  
  def GetConnectControl(self):
    shead = '''
#:kivy 1.9.0

AnchorLayout:
  anchor_x: 'center'
  anchor_y: 'bottom'
  size_hint: None, None
  size: root.width, root.height * 0.95
  GridLayout:
    size_hint: None, None
    size: root.width, root.width/6 + root.width/12 + (root.width - root.width/12*4)/3
    spacing: root.width/12, 0
    padding: root.width/12, root.width/6, root.width/12, 0
    cols: 3
    Label:
      size_hint: 1, None
      height: root.width/12
    Label:
      size_hint: 1, None
      height: root.width/12
      text_size: self.size
      font_size: root.width/30
      text: "{$recordtime}"
      halign: 'center'
      valign: 'top'
      markup: True
    Label:
      size_hint: 1, None
      height: root.width/12
    '''
    sdetail = '''
    Button:
      size_hint: 1, None
      height: (root.width - root.width/12*4)/3
      color: {$color}
      disabled_color: {$disabled_color}
      disabled: {$disabled}
      text: "{$text}"
      font_size: root.width/38
      text_size: self.size
      halign: 'center'
      valign: 'middle'
      background_normal: '{$background_normal}'
      background_down: '{$background_down}'
      background_disabled_normal: '{$background_disabled_normal}'
      background_disabled_down: '{$background_disabled_down}'
      always_release: False
      '''
    sbtnbuzzer = sdetail
    for key, value in self.btnconctrl[0].items():
      sbtnbuzzer = sbtnbuzzer.replace("{$%s}" %key, value)
    sbtnrecord = sdetail
    for key, value in self.btnconctrl[1].items():
      sbtnrecord = sbtnrecord.replace("{$%s}" %key, value)
    sbtnpreview = sdetail
    for key, value in self.btnconctrl[2].items():
      sbtnpreview = sbtnpreview.replace("{$%s}" %key, value)
    stime = "[color=0000ff]%s - %d[/color]\\n" %(self.scenename,self.scenecount) + ("[color=ff0000]%s[/color]" %self.recordtime if self.recordtime <> "" else "")
    shead = shead.replace("{$recordtime}",stime)
    #shead = shead.replace("{$recordtime}","11.22.33")
    shead += sbtnbuzzer + sbtnrecord + sbtnpreview
    #print shead.replace("root.width",str(self.width)).replace("root.height",str(self.height))
    return shead.replace("root.width",str(self.width)).replace("root.height",str(self.height))

  def BuildConnectControl(self, *largs):
    txt = self.GetConnectControl()
    if txt == self.textctrlbtn:
      return
    kv_container = self.current_screen.children[0]
    kv_widget = kv_container.children[0]
    for child in kv_container.children[:]:
      if isinstance(child, AnchorLayout):
        kv_widget = child
        break
    try:
      parser = Parser(content=txt)
      if isinstance(kv_widget, AnchorLayout):
        kv_container.remove_widget(kv_widget)
      widget = Factory.get(parser.root.name)()
      Builder._apply_rule(widget, parser.root, parser.root)
      widget.children[0].children[2].bind(on_release=self.Connect)
      widget.children[0].children[1].bind(on_release=self.Record)
      widget.children[0].children[0].bind(on_release=self.Buzzer)
      self.btnpreview = widget.children[0].children[0]
      self.btnrecord = widget.children[0].children[1]
      self.btnbuzzer = widget.children[0].children[2]
      #self.lblscenecount = widget.children[0].children[3]
      self.lblrecordtime = widget.children[0].children[4]
      #self.lblscenename = widget.children[0].children[5]
      #print "self.lblrecordtime.text",self.lblrecordtime.text
      kv_container.add_widget(widget)
      self.textctrlbtn = txt
    except (SyntaxError, ParserException) as e:
      print "BuildConnectControl: SyntaxError, ParserException", e
    except Exception as e:
      print "BuildConnectControl: Exception", e
      
  def DoRefreshConnectControl(self):
    time.sleep(30)
    while True:
      time.sleep(30)
      print "DoRefreshConnectControl"
      self.RefreshConnectControl()
  
  def RefreshConnectControl(self, timewait = 0):
    Clock.unschedule(self.BuildConnectControl)
    if timewait == 0:
      Clock.schedule_once(self.BuildConnectControl)
    else:
      Clock.schedule_once(self.BuildConnectControl, timewait)
      
  def RefreshAllControls(self, btnicon):
    #pngfile = __file__.replace(basename(__file__), ("data/%s-.png" %time.ctime()).replace(':',''))
    #Window.screenshot(name=pngfile)
    #time.sleep(1)
    #print "RefreshAllControls"
    #self.textctrlbtn = ""
    #*#self.RefreshConnectControl(1)
    #self.textcaminfo = ""
    #self.RefreshCameraInformation(1)
    #print self.timecontitle
    self.timecontitle = 0.0
    self.RefreshConnectTitle()
    
class XPonerineApp(App):
  version = __version__
  def build(self):
    self.appexit = threading.Event()
    evt = []
    evt.append(self.appexit)
    xponerine = XPonerine(evt)
    xponerine.duration = 0.7

    xponerine.screen = [XConnectScreen(name="mconnect")]
    xponerine.switch_to(xponerine.screen[0])
    xponerine.InitialCamIcon()
    return xponerine
    
  def on_pause(self):
    return True
    
  def on_resume(self):
    pass
    
  def on_stop(self):
    self.appexit.set()
    for thread in threading.enumerate():
      if thread.isAlive():
        print "APP.on_stop kill: %s" %thread.name
        try:
          thread._Thread__stop()
        except:
          pass

if __name__ == '__main__':
  XPonerineApp().run() 
