
from logHandler import log

import wx
import gui

import braille
import inputCore

from brailleInput import BrailleInputGesture

from  winusbpy import WinUsbPy


## how often (ms )  do we read keystrokes from device
read_freq = 50
## when we handle multiple id's, we'll need to revisit this.
vid = "1209" 
pid = "abc0"
## Just hardwiring, rather than querying the proper way
read_pipe_id = 129
write_pipe_id = 1


class BrailleDisplayDriver(braille.BrailleDisplayDriver):
        name = "brailleme"
        description = "BrailleMe Display"

        @classmethod
        def check(cls):
                return True
        
        def __init__(self):
                super(BrailleDisplayDriver, self).__init__()
                self._connectToDevice()
                ## 
                self._timer = wx.PyTimer(self._timerCallback)
                self._timer.Start(read_freq)

        def _connectToDevice(self):
                self._dev = WinUsbPy()
                if not self._dev.list_usb_devices(deviceinterface=True, present=True):
                        self._dev.close_winusb_device()
                        self._dev = None                        
                        raise RuntimeError("No display found : USB Enumeration Failed")
                # When we support multiple vid/pid ...
                if not self._dev.init_winusb_device(vid, pid):
                        self._dev.close_winusb_device()
                        self._dev = None                        
                        raise RuntimeError("No display found : Device Initialization Failed")
                ## get cell count
                self.do_init_seq()
                val = ""
                self._dev.overlapped_read_init(read_pipe_id, 64);                
                while len(val) == 0:
                        val = self._dev.overlapped_read(read_pipe_id);
                if len(val) == 10 and val[0] == '\xfa' and val[9] == '\xfb':
                        if val[1] == '\x02' and val[2] == '\x01':
                                self._cell_count = ord(val[3])
                self._connected = True
                
        def _timerCallback(self):
                if self._connected:
                        self._asyncRead();
                elif self._retry > 0:
                        self._retry = self._retry - 1
                else:
                        self._retry = 10
                        self._connectToDevice();
                        
        def _asyncRead(self):
                try_read = self._dev.overlapped_read(read_pipe_id);
                if  try_read == None:
                        self._dev.close_winusb_device()
                        self._dev = None                        
                        self._connected = False
                        self._retry = 10
                        raise RuntimeError("Error communicating with BraillMe Device %d",self._dev.get_last_error_code())
                if len(try_read) == 0:
                        return
                ( key, cur ) = self.decode_key(try_read)
                if key:
                        inputCore.manager.executeGesture(KeyGesture(key))
                if cur:
                        inputCore.manager.executeGesture(CursorGesture(cur - 1))
                                

        def do_init_seq(self):
                hdr  = '\xfb\xfb\x01\xf0\x20\x00'
                data = '\x00' * 32
                tail = '\xf1\xf2\x00\x00\xf3\x00\x00\x00\x00\xd7\xfd\xfd'
                todo = hdr+data+tail
                self._dev.write(write_pipe_id,todo)      

        def do_term_seq(self):
                hdr  = '\xfe\xfe\x01\xf0\x14\x00'
                data = '\x00' * 20
                tail = '\xf1\xf2\x00\x00\xf3\x00\x00\x00\x00\xd7\xfd\xfd'
                todo = hdr+data+tail
                self._dev.write(write_pipe_id,todo)

        def terminate(self):
                super(BrailleDisplayDriver, self).terminate()
                self._timer.Stop()
                self._timer  = None
                self.do_term_seq();
                self._dev.close_winusb_device()
                self._dev = None


        def _get_numCells(self):
                return self._cell_count
        
        
        def display(self,cells):
                line  = '\xfc\xfc\x01\xf0\x14\x00' + \
                        "".join(chr(cell) for cell in cells) +  \
                        '\xf1\xf2\x00\x00\xf3\x00\x00\x00\x00\xd7\xfd\xfd'
                self._dev.write(write_pipe_id,line)

                
        def decode_key(self,val):
                if len(val) == 10 and val[0] == '\xfa' and val[9] == '\xfb':
                        if val[1] == '\x00' and val[2]  == '\x01':
                                return ( None, ord(val[3]))
                        if val[1] == '\x01' :
                                return ( ord(val[7]) * 256 * 256 * 256 + 
                                         ord(val[6]) * 256 * 256 + 
                                         ord(val[5]) * 256 + 
                                         ord(val[4]) , None )
                return (None, None)
  


        gestureMap = inputCore.GlobalGestureMap({
                "globalCommands.GlobalCommands": {
                        "braille_routeTo"                : ("br(brailleme):routing"                             ,),
                        "kb:backspace"		         : ("br(brailleme):space+dot7"                          ,),
                        "kb:enter"                       : ("br(brailleme):dot8"                                ,),
                        "kb:escape"			 : ("br(brailleme):space+dot1+dot2+dot3+dot4+dot5+dot6" ,),
                        "kb:delete"			 : ("br(brailleme):space+dot8"                          ,),
                        "braille_previousLine"		 : ("br(brailleme):leftup"                              ,),
                        "braille_nextLine"		 : ("br(brailleme):leftdown"                            ,),
                        "braille_scrollBack"		 : ("br(brailleme):rightup"                             ,),
                        "braille_scrollForward"		 : ("br(brailleme):rightdown"                           ,),
                        "kb:leftAlt"			 : ("br(brailleme):space+dot2"                          ,),
                        "kb:tab"			 : ("br(brailleme):space+dot5"                          ,),
                        "kb:shift+alt+tab"		 : ("br(brailleme):space+dot2+dot4+dot5"                ,),
                        "kb:alt+tab"			 : ("br(brailleme):space+dot2+dot5"                     ,),
                        "kb:shift+tab"			 : ("br(brailleme):space+dot4+dot5"                     ,),
                        "kb:end"			 : ("br(brailleme):space+dot6+dot8"                     ,),
                        "kb:control+end"		 : ("br(brailleme):space+dot1+dot6+dot8"                ,),
                        "kb:home"			 : ("br(brailleme):space+dot3+dot8"                     ,),
                        "kb:control+home"		 : ("br(brailleme):space+dot1+dot3+dot8"                ,),
                        "kb:leftArrow"			 : ("br(brailleme):space+rightup"                       ,),
                        "kb:control+shift+leftArrow"	 : ("br(brailleme):space+dot1+dot4+rightup"             ,),
                        "kb:control+leftArrow"		 : ("br(brailleme):space+dot1+rightup"                  ,),
                        "kb:shift+alt+leftArrow"	 : ("br(brailleme):space+dot2+dot4+rightup"             ,),
                        "kb:alt+leftArrow"		 : ("br(brailleme):space+dot2+rightup"                  ,),
                        "kb:rightArrow"			 : ("br(brailleme):space+rightdown"                     ,),
                        "kb:control+shift+rightArrow"	 : ("br(brailleme):space+dot1+dot4+rightdown"           ,),
                        "kb:control+rightArrow"		 : ("br(brailleme):space+dot1+rightdown"                ,),
                        "kb:shift+alt+rightArrow"	 : ("br(brailleme):space+dot2+dot4+rightdown"           ,),
                        "kb:alt+rightArrow"		 : ("br(brailleme):space+dot2+rightdown"                ,),
                        "kb:pageUp"			 : ("br(brailleme):space+dot3"                          ,),
                        "kb:control+pageUp"		 : ("br(brailleme):space+dot1+dot3"                     ,),
                        "kb:upArrow"			 : ("br(brailleme):space+leftup"                        ,),
                        "kb:control+shift+upArrow"	 : ("br(brailleme):space+dot1+dot4+leftup"              ,),
                        "kb:control+upArrow"		 : ("br(brailleme):space+dot1+leftup"                   ,),
                        "kb:shift+alt+upArrow"		 : ("br(brailleme):space+dot2+dot4+leftup"              ,),
                        "kb:alt+upArrow"		 : ("br(brailleme):space+dot2+leftup"                   ,),
                        "kb:shift+upArrow"		 : ("br(brailleme):space+dot4+leftup"                   ,),
                        "kb:pageDown"			 : ("br(brailleme):space+dot6"                          ,),
                        "kb:control+pageDown"		 : ("br(brailleme):space+dot1+dot6"                     ,),
                        "kb:downArrow"			 : ("br(brailleme):space+leftdown"                      ,),
                        "kb:control+shift+downArrow"	 : ("br(brailleme):space+dot1+dot4+leftdown"            ,),
                        "kb:control+downArrow"		 : ("br(brailleme):space+dot1+leftdown"                 ,),
                        "kb:shift+alt+downArrow"	 : ("br(brailleme):space+dot2+dot4+leftdown"            ,),
                        "kb:alt+downArrow"		 : ("br(brailleme):space+dot2+leftdown"                 ,),
                        "kb:shift+downArrow"		 : ("br(brailleme):space+dot4+leftdown"                 ,),
                        "kb:capsLock"                    : ("br(brailleme):dot7+dot8"                           ,),
                },
        })


  

class KeyGesture(braille.BrailleDisplayGesture,BrailleInputGesture):
        source = BrailleDisplayDriver.name
        def __init__(self, keys):
                super(KeyGesture, self).__init__()
                if keys <= 0x7F:
                        self.dots = keys
                        self.space = False
                        self.id = None
                elif keys == 0x100:
                        self.dots = 0
                        self.space = True
                        self.id = None
                else:
                        self.dots = None
                        self.space = None
                        name = []
                        if keys & ( 1 << 8 ) : name.append('space') 
                        name.extend(["dot"+str(dot + 1) for dot in xrange(8) if keys & (1 << dot)])
                        if keys & ( 1 << 9 ) : name.append('leftup') 
                        if keys & ( 1 << 10 ): name.append('leftdown') 
                        if keys & ( 1 << 11 ): name.append('rightup') 
                        if keys & ( 1 << 12 ): name.append('rightdown') 
                        name = list(set(name))
                        self.id =  "+".join(name)
                log.info("BrailleMe Key: Dots: %s, Space: %s, Key: %s" % ( self.dots,self.space,self.id))
              

class CursorGesture(braille.BrailleDisplayGesture):
        source = BrailleDisplayDriver.name
        def __init__(self, index):
                super(CursorGesture, self).__init__()
                self.id = "routing"
                self.routingIndex = index
                log.info("BrailleMe Route: %d" % ( self.routingIndex))
