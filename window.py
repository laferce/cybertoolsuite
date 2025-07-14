# 1. 底层绑定库
from shiboken6 import *
# 2. 标准库（字母序）
import copy,datetime,json,logging,pathlib,random,shutil,sqlite3,time
# 3. 系统级库（可能影响环境）
import ctypes,win32con,win32gui,win32process,win32ui
# 4. PySide6核心模块（层级顺序）
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtWebEngineCore import *
from PySide6.QtWebChannel import *
from PySide6.QtWebEngineWidgets import *
# 5. 进程/网络库（无强依赖，可延后）
import psutil,subprocess,webbrowser

def AddWatcher[T:typing.Callable](method:T)->T:
    @functools.wraps(method)
    def Watcher(*args:...,**keyargs:...)->T:
        try:return method(*args,**keyargs)
        except:
            t=traceback.format_exc()
            logging.getLogger('main').error(t)
    return Watcher

def AllowDrag(control:QWidget,action:Qt.DropAction,*accepttypes:Object,enter:typing.Callable[[QDragEnterEvent],None]|None=None,leave:typing.Callable[[QDragLeaveEvent],None]|None=None,move:typing.Callable[[QDragMoveEvent],None]|None=None)->None:
    def DragEnter(event:QDragEnterEvent)->None:
        if isinstance(event.source(),accepttypes):
            event.setDropAction(action)
            event.accept()
            if enter:enter(event)
    control.setAcceptDrops(True)
    control.dragEnterEvent=DragEnter
    if leave:control.dragLeaveEvent=leave
    if move:control.dragMoveEvent=move

def ChangeIcon(control:QWidget,icon:QIcon)->QWidget:
    if not control.icon() or control.icon().cacheKey()!=icon.cacheKey():control.setIcon(icon)
    return control

def CloseControl(control:QWidget)->None:
    control.deleteLater()
    control.setParent(None)

def CreateAnimation(control:QWidget,name:bytes,startvalue:typing.Any,endvalue:typing.Any,mirror:QWidget|None=None,immediately:bool=False)->QPropertyAnimation|None:
    m=mirror or control
    if name==b'opacity':a=QPropertyAnimation(CreateEffect(m,QGraphicsOpacityEffect,startvalue),name,m)
    else:
        a=QPropertyAnimation(m,name,m)
        a.setEasingCurve(QEasingCurve.Type.OutElastic)
    a.setDuration(appconfig['general']['animetime']*1000)
    a.setStartValue(startvalue)
    a.setEndValue(endvalue)
    if mirror:
        a.finished.connect(lambda:CloseControl(m) or (control.show() if control.parent() else None))
        a.stateChanged.connect(lambda i,j:control.hide() if i==QAbstractAnimation.State.Running and j==QAbstractAnimation.State.Stopped else None)
    return a.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped) if immediately else a

def CreateAnimationsByParallel(owner:QWidget,animations:list[QPropertyAnimation],finished:typing.Callable[[],None]|None=None)->None:
    d=QParallelAnimationGroup(owner)
    for i in animations:d.addAnimation(i)
    if finished:d.finished.connect(finished)
    d.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

def CreateControl[T:QWidget](controltype:typing.Type[T],parent:QWidget|None,left:int,top:int,width:int,height:int,text:str='',click:typing.Callable|None=None,tooltip:str='',icon:QIcon|None=None)->T:
    c=controltype(text,parent) if text else controltype(parent)
    c.setGeometry(left,top,width if width>-1 else WidthByPixels(text)+8,height)
    if isinstance(c,QAbstractButton):c.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    if click:c.clicked.connect(click)
    if tooltip:c.setToolTip(tooltip)
    if icon:c.setIcon(icon)
    if parent:c.show()
    return c

def CreateEffect[T:QGraphicsEffect](control:QWidget,effecttype:typing.Type[T],value:typing.Any)->T:
    g=effecttype(control)
    g.__setattr__({QGraphicsBlurEffect:'blurRadius',QGraphicsOpacityEffect:'opacity'}[effecttype],value)
    control.setGraphicsEffect(g)
    return g

def CreateMirror(control:QWidget,parent:QWidget)->QLabel:
    m=CreateControl(QLabel,parent,*parent.mapFromGlobal(control.mapToGlobal(QPoint())).toTuple(),*control.size().toTuple())
    m.setPixmap(control.grab())
    return m

def FileOperation(operation:str,*filenames:str)->bool:
    if not GetExistsFileName(filenames[0]):return False
    match operation:
        case 'c':shutil.copy2(*filenames)
        case 'd':pathlib.Path(filenames[0]).unlink()
        case 'x':shutil.move(*filenames)
    return True

def FindAncestor[T:QWidget](control:QWidget,*ancestortype:typing.Type[T])->T|None:
    p=control
    while p and not isinstance(p,ancestortype or (QDialog,QMainWindow)):p=p.parent()
    return p

def FindControlAtPosition[T:QWidget](control:QWidget,position:QPoint,*controltype:typing.Type[T])->T|None:
    t=FindTopWindow()
    return FindAncestor(t.childAt(t.mapFromGlobal(control.mapToGlobal(position))),controltype)

def FindTopWindow(bottom:QMainWindow|QDialog|None=None)->QMainWindow|QDialog:
    w=bottom or next(i for i in QApplication.topLevelWidgets() if isinstance(i,(QDialog,MainWindow)) and i.isVisible())
    while (c:=next((i for i in w.findChildren(QDialog,options=Qt.FindChildOption.FindDirectChildrenOnly) if i.isVisible()),None)):w=c
    return w

def FindWindow(process:subprocess.Popen[bytes])->tuple[int,int,int]:
    try:
        p=psutil.Process(process.pid)
        while not p.children():time.sleep(0.1)
        q=p.children()[0].pid
        while True:
            h=win32gui.GetWindow(win32gui.GetDesktopWindow(),win32con.GW_CHILD)
            while h:
                if win32process.GetWindowThreadProcessId(h)[1]==q and not win32gui.GetParent(h) and win32gui.IsWindowVisible(h):return p.pid,q,h
                h=win32gui.GetWindow(h,win32con.GW_HWNDNEXT)
    except:return 0,0,0

def GetButtonIconName(config:dict)->str:
    if config['type']=='url':return f'file:///{apppath}/{GetExistsFileName(f'resources/shortcuts/{config['name']}.ico') or 'resources/icons/edge.png'}'
    elif (config['path'],config['file']) in [('.','cmd.exe'),('.','powershell.exe')]:return f'file:///{apppath}/resources/icons/{config['icon']}.png'
    elif GetExistsFileName(f'{config['path']}/{config['file'].strip('"').split(' ')[-1]}'):
        if config['icon']:return f'file:///{apppath}/resources/icons/{config['icon']}.png'
        elif config['prefix'][:4]=='java':return f'file:///{apppath}/resources/icons/java.png'
        elif config['prefix']=='python':return f'file:///{apppath}/resources/icons/python.png'
        elif config['type']=='cmd':return f'file:///{apppath}/resources/icons/cmd.png'
        else:
            b=QBuffer()
            GetFileIcon(f'{config['path']}/{config['file']}').pixmap(32,32).save(b,'PNG')
            return f'data:image/png;base64,{base64.b64encode(b.data()).decode()}'
    else:return f'file:///{apppath}/resources/icons/stopped.png'

def GetExistsFileName(filename:str)->str:
    return filename if pathlib.Path(filename).is_file() else ''

def GetFileIcon(filename:str)->QIcon:
    return appiconprovider.icon(QFileInfo(filename))

def GetOutputFormat(prefix:str,filenames:list[str])->list[str]:
    return ['/'.join(filenames[0].removeprefix(prefix).split('/')[:-1]),','.join(sorted(f'*.{i}' for i in {i.split('/')[-1].split('.')[-1].lower() for i in filenames})[:5])]

def GetPrefix(key:str)->str:
    p=appconfig['environment'].get(key)
    if key=='python':return PathSynthesis(apppath,p) if p else 'python'
    elif key[:4]=='java':return (GetPrefix(p) if key=='java' else f'{PathSynthesis(apppath,p)} -jar') if p else 'java -jar'
    else:return p or key

def GetUrlIcon(name:str)->QIcon:
    return QIcon(GetExistsFileName(f'resources/shortcuts/{name}.ico') or 'resources/icons/edge.png')

def MoveControl(control:QWidget,parent:QWidget,left:int|None=None,top:int|None=None,width:int|None=None,height:int|None=None)->None:
    if not all(i is None for i in [left,top,width,height]):control.setGeometry(control.x() if left is None else left,control.y() if top is None else top,control.width() if width is None else width,control.height() if height is None else height)
    control.setParent(parent)
    if parent:control.show()

def PathSynthesis(*filenames:str)->str:
    return filenames[-1] if ':' in filenames[-1] else '/'.join(filenames).replace('//','/')

def PixmapTranslucent(pixmap:QPixmap,achannel:int)->QPixmap:
    t=QPixmap(pixmap.size())
    t.fill(Qt.GlobalColor.transparent)
    p=QPainter(t)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
    p.drawPixmap(0,0,pixmap)
    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
    p.fillRect(t.rect(),QColor(0,0,0,achannel))
    p.end()
    return t

def RandomName(formatname:str,existnames:list[str])->str:
    return next(i for i in iter(lambda:formatname%random.randint(0,99999999),None) if i not in existnames)

def ReadDatabase(sql:str,*data:...)->list:
    with sqlite3.connect('resources/data.db') as c:return c.execute(sql,data).fetchall()

def ReadFile(filename:str,jsonmode:bool=False)->dict|list|str|None:
    try:
        with pathlib.Path(filename).open(encoding='utf-8') as r:return json.load(r) if jsonmode else r.read()
    except:return None

def RequestFile(kind:str,parent:QWidget,title:str,dir:str,filter:str='')->tuple[str|list[str],str]:
    d=QFileDialog(parent,title,dir,filter,fileMode={'file':QFileDialog.FileMode.ExistingFile,'files':QFileDialog.FileMode.ExistingFiles}[kind])
    d.setWindowModality(Qt.WindowModality.WindowModal)
    t=d.exec()
    s=d.selectedFiles()
    r=(s if kind=='files' else s[0] if s else '')*t,d.selectedNameFilter()*t
    CloseControl(d)
    return r

def RequestInput(parent:QWidget,title:str,text:str,mode:QLineEdit.EchoMode=QLineEdit.EchoMode.Normal,default:str='')->tuple[bool,str]:
    d=QInputDialog(parent)
    d.setCancelButtonText('取消')
    d.setInputMode(QInputDialog.InputMode.TextInput)
    d.setLabelText(text)
    d.setOkButtonText('确定')
    d.setTextEchoMode(mode)
    d.setTextValue(default)
    d.setWindowModality(Qt.WindowModality.WindowModal)
    d.setWindowTitle(title)
    r=d.exec(),d.textValue()
    CloseControl(d)
    return bool(r[0]),r[1]*r[0]

def RequestMessage(kind:str,parent:QWidget,title:str,text:str,buttons:QMessageBox.StandardButton=QMessageBox.StandardButton.Ok,default:QMessageBox.StandardButton=QMessageBox.StandardButton.NoButton)->QMessageBox.StandardButton:
    b={QMessageBox.StandardButton.Ok:'确定',QMessageBox.StandardButton.Cancel:'取消',QMessageBox.StandardButton.Yes:'是(&Y)',QMessageBox.StandardButton.No:'否(&N)'}
    d=QMessageBox({'c':QMessageBox.Icon.Critical,'i':QMessageBox.Icon.Information,'q':QMessageBox.Icon.Question,'w':QMessageBox.Icon.Warning}[kind],title,text,buttons,parent)
    d.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
    d.setDefaultButton(default)
    d.setWindowModality(Qt.WindowModality.WindowModal)
    for i in d.buttons():i.setText(b[d.standardButton(i)])
    return d.exec()

def Reshape(control:QWidget,event:QResizeEvent)->None:
    if control.anchors and (w:=event.oldSize().width())>-1 and (h:=event.oldSize().height())>-1:
        x,y=control.width()-w,control.height()-h
        for i in control.anchors:
            a,b,c,d=i[0]//3==1,i[0]%3==1,i[0]//3==2,i[0]%3==2
            if a or b:any(j.move(j.x()+x*a,j.y()+y*b) for j in i[1:])
            if c or d:any(j.resize(j.width()+x*c,j.height()+y*d) for j in i[1:])

def SelectFile(filename:str)->None:
    p=ctypes.c_void_p()
    ctypes.windll.shell32.SHParseDisplayName(filename.replace('./','').replace('/','\\'),None,ctypes.byref(p),0,None)
    if p:
        ctypes.windll.shell32.SHOpenFolderAndSelectItems(p,0,None,0)
        ctypes.windll.shell32.ILFree(p)

def StartDrag(control:QWidget,border:bool=False)->None:
    w,h=control.width(),control.height()
    d=QDrag(control)
    if border:
        b=CreateControl(QFrame,control,0,0,w,h)
        b.setStyleSheet('border:2px solid gray')
    d.setMimeData(QMimeData())
    d.setHotSpot(QPoint(w//2,h//2))
    d.setPixmap(PixmapTranslucent(control.grab(QRect(0,0,w,h)),224))
    d.exec(Qt.DropAction.CopyAction|Qt.DropAction.MoveAction)
    if border:CloseControl(b)

def Terminate(pid:int)->bool:
    try:
        p=psutil.Process(pid)
        if all(Terminate(i.pid) for i in p.children()):
            p.terminate()
            p.wait()
            return not p.is_running()
        else:return False
    except psutil.NoSuchProcess:return True
    except:return False

def TryGet(method:typing.Callable,exceptions:typing.Type[BaseException]|list[typing.Type[BaseException]]|None=None,*args:...,**kwargs:...)->typing.Any|None:
    try:return method(*args,**kwargs)
    except BaseException as e:
        if any(isinstance(e,i) for i in exceptions or []):raise
        return None

def WidthByCharacters(text:str)->int:
    return (len(text)+len(text.encode('utf-8')))//2

def WidthByPixels(text:str)->int:
    return WidthByCharacters(text)*6

def WriteDatabase(sql:str,*data:...)->None:
    with sqlite3.connect('resources/data.db') as c:
        c.execute(sql,data)
        c.commit()

def WriteDatabaseMany(sql:str,data:list)->None:
    with sqlite3.connect('resources/data.db') as c:
        c.executemany(sql,data)
        c.commit()

def WriteFile(filename:str,text:dict|list|str,jsonmode:bool=False)->None:
    with pathlib.Path(filename).open('w',encoding='utf-8') as w:json.dump(text,w,ensure_ascii=False,indent=4) if jsonmode else w.write(text)

class ChannelBridge(QObject):
    
    def __init__(self,method:typing.Callable[[list],None])->None:
        super().__init__()
        self.method=method
    @Slot(list)
    def Method(self,argument:list)->None:
        self.method(argument)

class ProcessNode:
    
    def __init__(self,name:str='',process:psutil.Process|None=None,parent:'ProcessNode|None'=None,isroot:bool=True)->None:
        n=[psutil.NoSuchProcess]
        self.children=[]
        self.cmdline=TryGet(process.cmdline,n) or [] if process else []
        self.argument='\n'.join(f'{'　'*bool(i)*3}{j}' for i,j in enumerate(self.cmdline))
        self.lifecycle=7
        self.name=name
        self.parent=parent
        self.path=TryGet(process.exe,n) or '' if process else ''
        self.file=self.path.split('\\')[-1]
        self.pid=process.pid if process else 0
        self.root=self if isroot else parent.root
        self.time=datetime.datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S') if process else ''
        self.user=TryGet(process.username,n) or '' if process else ''
        if parent:parent.children.append(self)
    @AddWatcher
    def Layer(self)->int:
        return 0 if self.parent is None else self.parent.Layer()+1
    @AddWatcher
    def Row(self)->int:
        return self.parent.children.index(self) if self.parent and self in self.parent.children else -1

class ProcessTreeModel(QAbstractItemModel):
    @AddWatcher
    def __init__(self)->None:
        super().__init__()
        self.filter=''
        self.header=['进程名','进程号','工具名']
        self.root=ProcessNode()
        self.rootoffscreen=None
    @AddWatcher
    def RefreshTree(self,processlist:list)->None:
        self.beginResetModel()
        self.rootoffscreen=copy.deepcopy(self.root)
        self.root.children.clear()
        self.__rebuidtree(self.rootoffscreen,processlist)
        self.root=self.rootoffscreen
        self.endResetModel()
    @AddWatcher
    def __rebuidtree(self,node:ProcessNode,processlist:list|None=None)->None:
        p=[i.pid for i in node.children]
        if node is self.rootoffscreen:
            for i in [i for i in processlist if i[1] not in p]:
                try:ProcessNode(i[0],psutil.Process(i[1]),node)
                except:pass
        else:
            try:
                for i in [i for i in psutil.Process(node.pid).children() if i.pid not in p]:
                    try:ProcessNode('',i,node,False)
                    except:pass
            except:pass
        for i in node.children:self.__rebuidtree(i)
        for i in node.children.copy():
            try:
                if node is self.rootoffscreen:i.name=next(j for j in processlist if j[1]==i.pid)[0]
                if i.lifecycle in [3,4]:i.lifecycle=(psutil.Process(i.pid).status()==psutil.STATUS_RUNNING)+3
                else:i.lifecycle-=1
            except:
                if i.lifecycle>2:i.lifecycle=2
                else:i.lifecycle-=1
            if not i.lifecycle:node.children.remove(i)
    @AddWatcher
    def columnCount(self,parent:QModelIndex)->int:
        return 3
    @AddWatcher
    def data(self,index:QModelIndex,role:Qt.ItemDataRole)->int|str|QBrush|QIcon|None:
        if not index.isValid():return None
        n=index.internalPointer()
        match role:
            case Qt.ItemDataRole.BackgroundRole:
                return QBrush(Qt.GlobalColor.red if n.lifecycle<3 else Qt.GlobalColor.gray if n.lifecycle==3 else Qt.GlobalColor.green if n.lifecycle>4 else Qt.GlobalColor.magenta if n.root.name.startswith('[待捕捉] ') else Qt.GlobalColor.darkRed if n.user!=appuser else Qt.GlobalColor.transparent)
            case Qt.ItemDataRole.DecorationRole:
                if not index.column():return GetFileIcon(n.path)
            case Qt.ItemDataRole.DisplayRole:return [n.file,n.pid,n.name][index.column()]
            case Qt.ItemDataRole.ForegroundRole:
                if self.filter and self.filter in f'{n.file.lower()}\n{n.name.lower()}':return QBrush(Qt.GlobalColor.blue)
            case Qt.ItemDataRole.ToolTipRole:return f'文件：{n.path}\n参数：{n.argument}\n用户：{n.user}\n启动：{n.time}'
        return None
    @AddWatcher
    def headerData(self,section:int,orientation:Qt.Orientation,role:Qt.ItemDataRole)->str:
        if orientation!=Qt.Orientation.Horizontal or role!=Qt.ItemDataRole.DisplayRole:return None
        return self.header[section]
    @AddWatcher
    def index(self,row:int,column:int,parent:QModelIndex)->QModelIndex:
        p=parent.internalPointer() if parent.isValid() else self.root
        return self.createIndex(row,column,p.children[row]) if 0<=row<len(p.children) else QModelIndex()
    @AddWatcher
    def parent(self,index:QModelIndex)->QModelIndex:
        return self.createIndex(r,0,p.parent) if isinstance(p:=index.internalPointer(),ProcessNode) and p.parent is not self.root and (r:=p.parent.Row())>-1 else QModelIndex()
    @AddWatcher
    def rowCount(self,parent:QModelIndex)->int:
        return len((parent.internalPointer() if parent.isValid() else self.root).children)

class ShowErrorHandler(logging.Handler):

    def __init__(self)->None:
        super().__init__()
        self.records=[]
        self.setLevel(logging.ERROR)
    
    def emit(self,record:logging.LogRecord)->None:
        self.records.append([datetime.datetime.now().timestamp(),record])
        n=len(self.records)
        if n<3:RequestMessage('c',FindTopWindow(),'错误',f'错误信息已保存到 errors.log 文件，请向作者提供该文件以分析错误：\n{record.msg}')
        elif n>9 or self.records[-1][0]-self.records[-3][0]<1 or RequestMessage('c',FindTopWindow(),'错误',f'报错太多，是否强制退出程序？\n{record.msg}',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.Yes)==QMessageBox.StandardButton.Yes:
            FileOperation('x','resources/pyvenv.cfg','pyvenv.cfg')
            mainwindow.tab_area.CleanUp(appconfig['general']['grab']+3)
            os._exit(1)

class WindowFounder(QThread):
    signaler=Signal(int,int,int)
    def __init__(self,path:str)->None:
        super().__init__()
        self.path=path

    def run(self)->None:
        self.signaler.emit(*FindWindow(subprocess.Popen(f'conhost cmd /k "cd /d {self.path}"',creationflags=subprocess.CREATE_NEW_CONSOLE)))

class RadioButtonGroup(QWidget):
    @AddWatcher
    def __init__(self,parent:QWidget,left:int,top:int,width:int,height:int,options:list[str],default:int=-1)->None:
        super().__init__(parent)
        w=width//len(options)
        self.setGeometry(left,top,width,height)
        self.radio_buttons=[CreateControl(QRadioButton,self,i*w,0,w,height,j) for i,j in enumerate(options)]
        for i in self.radio_buttons:i.setStyleSheet('spacing:0px;')
        if default>-1:self.radio_buttons[default].setChecked(True)
    @AddWatcher
    def GetValue(self)->int:
        return next((self.radio_buttons.index(i) for i in self.radio_buttons if i.isChecked()),-1)
    @AddWatcher
    def ReshapeItems(self,lefts:list[int],width:int)->None:
        for i,j in enumerate(self.radio_buttons):j.setGeometry(lefts[i],0,width,self.height())
    @AddWatcher
    def ResetTexts(self,texts:list[str])->None:
        for i,j in enumerate(self.radio_buttons):j.setText(texts[i])
    @AddWatcher
    def SetValue(self,value:int)->None:
        self.radio_buttons[value].setChecked(True)

class ScrollableGroup(QGroupBox):
    @AddWatcher
    def __init__(self,parent:QWidget,left:int,top:int,width:int,height:int,title:str='',scrollflag:int=0,boardflag:int=0,canvas:QWidget|None=None,helptext:str='')->None:
        super().__init__(title,parent)
        self.savedwidth=self.savedheight=0
        self.setGeometry(left,top-5,width,height+5)
        self.content_scroll=CreateControl(QScrollArea,self,5,13,width-10,height-13)
        self.horizontalbar=self.content_scroll.horizontalScrollBar()
        self.verticalbar=self.content_scroll.verticalScrollBar()
        self.content_canvas=canvas or QWidget()
        self.content_scroll.setWidget(self.content_canvas)

class WebArea(QWebEngineView):
    @AddWatcher
    def __init__(self,parent:QWidget,left:int,top:int,width:int,height:int,html:str,method:typing.Callable[[list],None]=lambda _:None,hider:typing.Callable[[],None]|None=None)->None:
        super().__init__(parent)
        self.bridge=ChannelBridge(method)
        self.channel=QWebChannel()
        self.channel.registerObject('bridge',self.bridge)
        self.hider=hider
        self.setGeometry(left,top,width,height)
        self.setHtml(html,QUrl(apppath))
        self.page().setWebChannel(self.channel)
        QShortcut(QKeySequence('Ctrl+C'),self).activated.connect(self.__shortcutctrlc)
        QShortcut(QKeySequence('Ctrl+Q'),self).activated.connect(self.__shortcutctrlq)
        self.web_menu=QMenu(self)
        self.copy_action=self.web_menu.addAction('复制','Ctrl+C',self.__shortcutctrlc)
        self.open_action=self.web_menu.addAction('打开','Ctrl+Q',self.__shortcutctrlq)
        self.find_area=CreateControl(QWidget,self,0,0,280,30)
        self.find_area.hide()
        self.find_text=CreateControl(QLineEdit,self.find_area,0,0,280,30)
        self.find_text.setStyleSheet('padding-left:5px;padding-right:115px;')
        self.find_text.keyReleaseEvent=self.__find_text_keyrelease
        self.find_text.textChanged.connect(self.__find_text_textchanged)
        self.find_count=CreateControl(QLabel,self.find_area,170,0,70,30)
        self.find_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.find_count.setStyleSheet('padding-top:9px;')
        self.find_preview=CreateControl(QToolButton,self.find_area,240,0,15,15,click=self.__find_preview)
        self.find_preview.setArrowType(Qt.ArrowType.UpArrow)
        self.find_preview.setAutoRaise(True)
        self.find_next=CreateControl(QToolButton,self.find_area,240,15,15,15,click=self.__find_next)
        self.find_next.setArrowType(Qt.ArrowType.DownArrow)
        self.find_next.setAutoRaise(True)
        self.find_hide=CreateControl(QToolButton,self.find_area,255,5,20,20,click=self.__find_hide)
        self.find_hide.setAutoRaise(True)
        self.find_hide.setText('×')
    @AddWatcher
    def WebFinderSwitch(self)->None:
        if self.find_area.isVisible():
            self.find_text.setText('')
            self.find_count.setText('')
            self.findText('')
            self.find_area.hide()
            if self.hider:self.hider()
        else:
            self.find_area.show()
            self.find_area.move(self.width()-285,5)
            self.find_text.setText(self.page().selectedText())
            self.find_text.setFocus()
    @AddWatcher
    def __shortcutctrlc(self)->None:
        self.triggerPageAction(QWebEnginePage.WebAction.Copy)
    @AddWatcher
    def __shortcutctrlq(self)->None:
        if QUrl(self.page().selectedText()).scheme() in ['http','https']:webbrowser.open(self.page().selectedText())
    @AddWatcher
    def __searchcount(self,result:QWebEngineFindTextResult)->None:
        self.find_count.setText(f'{result.activeMatch()}/{result.numberOfMatches()}' if self.find_text.text() else '')
    @AddWatcher
    def __find_preview(self)->None:
        self.findText(self.find_text.text(),QWebEnginePage.FindFlag.FindBackward,self.__searchcount)
    @AddWatcher
    def __find_next(self)->None:
        self.findText(self.find_text.text(),QWebEnginePage.FindFlag.FindCaseSensitively,self.__searchcount)
    @AddWatcher
    def __find_hide(self)->None:
        self.WebFinderSwitch()
    @AddWatcher
    def __find_text_keyrelease(self,event:QKeyEvent)->None:
        match event.key():
            case Qt.Key.Key_Escape:self.WebFinderSwitch()
            case Qt.Key.Key_Down|Qt.Key.Key_Enter|Qt.Key.Key_Return:self.find_next.click()
            case Qt.Key.Key_Up:self.find_preview.click()
    @AddWatcher
    def __find_text_textchanged(self,text:str)->None:
        self.find_next.click()
    @AddWatcher
    def contextMenuEvent(self,event:QContextMenuEvent)->None:
        if (t:=self.page().selectedText()):
            self.open_action.setVisible(QUrl(t).scheme() in ['http','https'])
            self.web_menu.exec(event.globalPos())
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        self.find_area.move(self.width()-285,5)
        return super().resizeEvent(event)

class MainWindow(QMainWindow):

    def __init__(self)->None:
        super().__init__()
        m=logging.getLogger('main')
        m.setLevel(logging.ERROR)
        n=logging.FileHandler('errors.log',encoding='utf-8')
        n.setFormatter(logging.Formatter(f'{'-'*32}\n%(asctime)s\n%(name)s:%(message)s'))
        m.addHandler(n)
        m.addHandler(ShowErrorHandler())
        appconfig.update({'general':{'animetime':0.5,'preview':True,'grab':True},'favority':[],'history':{'record':True,'maxshown':99,'orderbycount':True},'process':{'autorefresh':True,'pintop':True},'environment':{'java':'','java8':'Java_path/Java_8_win/bin/java','java9+':'Java_path/Java_11_win/bin/java','python':'Python3.11.9/python'},'residual':[]}|(ReadFile('resources/config.json',True) or {}))
        self.htmlhead=f'<style>code{{color:blueviolet;cursor:pointer;}}.usage{{color:blue}}details summary{{list-style:none;}}details > summary::before{{content:url("{apppath}/resources/icons/closed.png");}}details[open] > summary::before{{content:url("{apppath}/resources/icons/opened.png");}}</style><input id="show" type="button" value="全部展开"> <input id="hide" type="button" value="全部收起"> <span style="color:blue;">点击蓝色标签替换命令</span> <span style="color:blueviolet;">点击紫色标签追加选项</span> 具体替换和追加的文本跟随标签内容变化'
        self.htmlroot=f'{ReadFile('resources/qwebchannel.js')}document.addEventListener("DOMContentLoaded",()=>{{new QWebChannel(qt.webChannelTransport,(channel)=>{{window.webchannel=channel.objects.bridge;}})}});'
        self.htmltail='document.getElementById("show").addEventListener("click",()=>{document.querySelectorAll("details").forEach(i=>{i.open=true})});document.getElementById("hide").addEventListener("click",()=>{document.querySelectorAll("details").forEach(i=>{i.open=false})});document.querySelectorAll("summary").forEach((i)=>{i.addEventListener("click",(e)=>{if(e.target.tagName=="CODE"||window.getSelection().toString()){e.preventDefault();}})});document.addEventListener("click",(e)=>{if(e.target.tagName=="CODE")webchannel.Method([e.target.className,e.target.innerText]);});'
        self.icons={i:QIcon(f'resources/icons/{i}.png') for i in ['finished','pause','play','stopped','cmd','powershell','java','python','edge']}|{i:QIcon('resources/icons/java.png') for i in ['java8','java9+']}
        self.kinds=[list(i) for i in ReadDatabase('SELECT name,type FROM kinds')]
        self.movie=QMovie('resources/icons/running.gif')
        self.movie.frameChanged.connect(self.__movieframechanged)
        self.pausedtool=False
        self.processdialog=None
        self.processlist=[]
        self.programkeys=['name','type','kind','prefix','path','file','output','format','icon','note','extra']
        self.programs=[{self.programkeys[j]:k or '' for j,k in enumerate(i)} for i in ReadDatabase('SELECT * FROM tools')]
        self.runninglist=[]
        self.searchkeywords=[False,'','']
        self.tools={i['name']:i for i in self.programs}
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True)
        self.setMinimumSize(1330,750)
        self.setStyleSheet('QGroupBox{border:1px solid gray;margin-top:5px;}QGroupBox::title{position:relative;subcontrol-origin:margin;left:10px;}QScrollArea{border:none;}')
        self.setWindowIcon(QIcon('resources/icons/toolbox.ico'))
        self.setWindowTitle('渗透测试集成工具箱 - 四川省德阳市公安局 李光')
        QShortcut(QKeySequence('Ctrl+C'),self).activated.connect(self.__shortcutctrlc)
        QShortcut(QKeySequence('Ctrl+F'),self).activated.connect(self.__shortcutctrlf)
        QShortcut(QKeySequence('Ctrl+V'),self).activated.connect(self.__shortcutctrlv)
        QShortcut(QKeySequence('Ctrl+X'),self).activated.connect(self.__shortcutctrlx)
        QShortcut(QKeySequence('F1'),self).activated.connect(self.__shortcutf1)
        QShortcut(QKeySequence('F2'),self).activated.connect(self.__shortcutf2)
        QShortcut(QKeySequence('F3'),self).activated.connect(self.__shortcutf3)
        QShortcut(QKeySequence('Shift+Delete'),self).activated.connect(self.__shortcutshiftdelete)
        self.tool_menu=QMenu(self)
        self.edit_action=self.tool_menu.addAction('编辑工具','',self.__edit_action)
        self.remove_action=self.tool_menu.addAction('移出列表','',self.__remove_action)
        self.favorite_action=self.tool_menu.addAction('添加收藏','',self.__favorite_action)
        self.output_menu=QMenu(self)
        self.output_menu.setToolTipsVisible(True)
        self.copy_action=self.output_menu.addAction('复制','Ctrl+C',self.__shortcutctrlc)
        self.cut_action=self.output_menu.addAction('剪切','Ctrl+X',self.__shortcutctrlx)
        self.paste_action=self.output_menu.addAction('粘贴','Ctrl+V',self.__shortcutctrlv)
        self.delete_action=self.output_menu.addAction('删除','Shift+Delete',self.__shortcutshiftdelete)
        self.output_menu.addSeparator()
        self.copypath_action=self.output_menu.addAction('复制路径','F1',self.__shortcutf1)
        self.rename_action=self.output_menu.addAction('重命名','F2',self.__shortcutf2)
        self.send_action=self.output_menu.addAction('发送到首页','F3',self.__shortcutf3)
        self.tab_area=TabArea(self,1310,730)
        self.preview_window=PreviewWindow(self)
        self.anchors=[[8,self.tab_area]]
        self.movie.start()
        QTimer.singleShot(100,self.__createhome)
        self.startTimer(1000)
        FileOperation('x','pyvenv.cfg','resources/pyvenv.cfg')
        # win32gui.SetProcessDPIAware()
    @AddWatcher
    def AppendUsing(self,name:str,ppid:int,cpid:int=0,hwnd:int=0)->None:
        try:
            if not cpid:
                p=psutil.Process(ppid)
                while not p.children():time.sleep(0.1)
                cpid=p.children()[0].pid
            appconfig['residual'].append([name,ppid,cpid,hwnd])
            self.SaveConfig()
            self.processlist.append([name,ppid])
        except:pass
    @AddWatcher
    def CheckProcess(self,name:str)->bool:
        t=self.tools[name]
        if t['type']=='url':return False
        n=t['name']
        if any(i.topic.title==n for i in self.tab_area.SortedTabs()[1:]) or any(i[0].removeprefix('[内嵌] ').removeprefix('[待捕捉] ')==n for i in self.processlist):return True
        return False
    @AddWatcher
    def HomePage(self)->'HomeTopic':
        return self.tab_area.SortedTabs()[0].topic
    @AddWatcher
    def RefreshTools(self,name:str,config:dict)->None:
        for i in self.HomePage().favorite_group.children()+self.HomePage().history_group.children():
            if i.name==name:i.RefreshConfig(config)
    @AddWatcher
    def SaveConfig(self)->None:
        WriteFile('resources/config.json',appconfig,True)
    @AddWatcher
    def SaveHistory(self,mode:int,*data:...)->None:
        WriteDatabase(['INSERT INTO history VALUES (?,?,?)','UPDATE history SET name=? WHERE name=?','DELETE FROM history WHERE name=?'][mode-1],*data)
    @AddWatcher
    def SaveKinds(self)->None:
        WriteDatabase('DELETE FROM kinds')
        WriteDatabaseMany('INSERT INTO kinds VALUES (?,?)',self.kinds)
    @AddWatcher
    def SaveTools(self,mode:int,tool:dict)->None:
        match mode:
            case 1:WriteDatabase(f'INSERT INTO tools VALUES ({','.join(['?']*len(self.programkeys))})',*[tool[i] or None for i in self.programkeys])
            case 2:
                WriteDatabase(f'UPDATE tools SET {','.join(f'{i}=?' for i in self.programkeys)} WHERE name=?',*[tool[i] or None for i in self.programkeys]+[tool['oldname']])
                if tool['name']!=tool['oldname']:
                    WriteDatabase('UPDATE reports SET tool=? WHERE tool=?',tool['name'],tool['oldname'])
                    FileOperation('x',f'resources/docs/{tool['oldname']}.html',f'resources/docs/{tool['name']}.html')
                    FileOperation('x',f'resources/shortcuts/{tool['oldname']}.ico',f'resources/shortcuts/{tool['name']}.ico')
                    appconfig['favorite']=[tool['name'] if i==tool['oldname'] else i for i in appconfig['favorite']]
                    self.SaveConfig()
                    self.SaveHistory(2,tool['name'],tool['oldname'])
            case 3:
                WriteDatabase('DELETE FROM tools WHERE name=?',tool['name'])
                WriteDatabase('DELETE FROM reports WHERE tool=?',tool['name'])
                FileOperation('d',f'resources/docs/{tool['name']}.html')
                FileOperation('d',f'resources/shortcuts/{tool['name']}.ico')
                appconfig['favorite']=[i for i in appconfig['favorite'] if i!=tool['name']]
                self.SaveConfig()
                self.SaveHistory(3,tool['name'])
        self.programs=[{self.programkeys[j]:k or '' for j,k in enumerate(i)} for i in ReadDatabase('SELECT * FROM tools')]
        self.tools={i['name']:i for i in self.programs}
    @AddWatcher
    def UseTool(self,name:str,augmented:bool)->None:
        t=self.tools[name]
        r=GetPrefix(t['prefix'])
        if t['type']=='url' or (t['path'],t['file']) in [('.','cmd.exe'),('.','powershell.exe')] or GetExistsFileName(f'{t['path']}/{t['file']}'):
            c=''
            match t['type']:
                case 'cmd':
                    if augmented:self.tab_area.AddTopic(EmbedCmdTopic(name),self.icons['stopped'])
                    else:
                        p=subprocess.Popen(c:=f'conhost cmd /k "cd /d {t['path']}"',creationflags=subprocess.CREATE_NEW_CONSOLE)
                        w=FindWindow(p)
                        for i in f'{r} {t['file']}':
                            win32gui.PostMessage(w[2],win32con.WM_CHAR,ord(i),0)
                            time.sleep(0.01)
                        self.AppendUsing(name,*w[:2])
                case 'ui':self.AppendUsing(name,subprocess.Popen(c:=f'cmd /c "cd /d {t['path']} && {r} {t['file']}"',creationflags=subprocess.CREATE_NO_WINDOW).pid)
                case 'url':
                    try:subprocess.Popen([t['file'],c:=t['path']]) #webbrowser.get(t['file']).open_new_tab(c:=t['path'])
                    except:webbrowser.open(c:=t['path'])
            if appconfig['history']['record']:self.SaveHistory(1,datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),name,c)
            self.HomePage().RefreshHistory()
        else:RequestMessage('w',self,'错误',f'工具“{name}”不存在')
    @AddWatcher
    def __createhome(self)->None:
        self.tab_area.AddTopic(HomeTopic())
        n=len(appconfig['residual'])
        for i in appconfig['residual'].copy():
            try:
                p=psutil.Process(i[1])
                q=p.children()
                if q and q[0].pid==i[2] and {p.name(),q[0].name()}=={'cmd.exe','conhost.exe'}:self.processlist.append([i[0].replace('[内嵌] ','[待捕捉] '),i[1]])
                else:appconfig['residual'].remove(i)
            except:appconfig['residual'].remove(i)
        if len(appconfig['residual'])!=n:self.SaveConfig()
    @AddWatcher
    def __currentembedcmd(self)->'EmbedCmdTopic|None':
        return self.tab_area.CurrentTab().topic if isinstance(self.tab_area.CurrentTab().topic,EmbedCmdTopic) else None
    @AddWatcher
    def __shortcutctrlc(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(d:=QApplication.focusWidget(),QListView) and (n:=[f'{c.outputpath}/{c.model.data(i)}' for i in d.selectedIndexes()]):
            m=QMimeData()
            m.setUrls([QUrl.fromLocalFile(i) for i in n])
            m.setData('application/x-qt-windows-mime;value="Preferred DropEffect"',b'\x01\x00\x00\x00')
            QApplication.clipboard().setMimeData(m)
    @AddWatcher
    def __shortcutctrlf(self)->None:
        if (c:=self.__currentembedcmd()) and c.help_browser.isVisible():c.help_browser.WebFinderSwitch()
    @AddWatcher
    def __shortcutctrlv(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(QApplication.focusWidget(),QListView) and (m:=QApplication.clipboard().mimeData()).hasUrls() and (n:=[i for i in (GetExistsFileName(i.toLocalFile()) for i in m.urls()) if i]):
            p=c.outputpath
            if m.hasFormat('application/x-qt-windows-mime;value="Preferred DropEffect"') and m.data('application/x-qt-windows-mime;value="Preferred DropEffect"')==b'\x02\x00\x00\x00':
                if '/'.join(n[0].split('/')[:-1])!=p and any(pathlib.Path(f'{p}/{i.split('/')[-1]}').exists() for i in n) and RequestMessage('q',self,'提示','存在重名文件，是否全部覆盖？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.No:return
                try:
                    for i in n:FileOperation('x',i,f'{p}/{i.split('/')[-1]}')
                    RequestMessage('i',self,'提示','文件剪切完成')
                except:RequestMessage('w',self,'警告','部分文件被占用，剪切失败')
            else:
                try:
                    for i in n:
                        r=1
                        q=f'{p}/{i.split('/')[-1]}'
                        s=q.split('/')
                        t=s[-1].split('.')
                        h=[f'{'/'.join(s[:-1])}/{'.'.join(t[:-1])}',t[-1]]
                        while pathlib.Path(q).exists():
                            q=f'{h[0]} ({r}).{h[1]}'
                            r+=1
                        FileOperation('c',i,q)
                    RequestMessage('i',self,'提示','文件复制完成')
                except:RequestMessage('w',self,'警告','部分文件被占用，复制失败')
    @AddWatcher
    def __shortcutctrlx(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(d:=QApplication.focusWidget(),QListView) and (n:=[f'{c.outputpath}/{c.model.data(i)}' for i in d.selectedIndexes()]):
            m=QMimeData()
            m.setUrls([QUrl.fromLocalFile(i) for i in n])
            m.setData('application/x-qt-windows-mime;value="Preferred DropEffect"',b'\x02\x00\x00\x00')
            QApplication.clipboard().setMimeData(m)
    @AddWatcher
    def __shortcutf1(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(d:=QApplication.focusWidget(),QListView) and len(n:=[f'{c.outputpath}/{c.model.data(i)}' for i in d.selectedIndexes()])==1:QApplication.clipboard().setText(n[0])
    @AddWatcher
    def __shortcutf2(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(d:=QApplication.focusWidget(),QListView) and len(n:=[f'{c.outputpath}/{c.model.data(i)}' for i in d.selectedIndexes()])==1 and (m:=RequestInput(self,'输入','重命名文件',default='.'.join(n[0].split('/')[-1].split('.')[:-1]))[0]):
            FileOperation('x',n[0],f'{c.outputpath}/{m}.{n[0].split('.')[-1]}')
            WriteDatabase('UPDATE reports SET filename=? WHERE tool=? AND filename=?',f'{m}.{n[0].split('.')[-1]}',c.title,c.model.data(d.selectedIndexes()[0]))
            for i in self.HomePage().history_group.children():
                if i.name==c.title:i.RefreshReports()
    @AddWatcher
    def __shortcutf3(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(d:=QApplication.focusWidget(),QListView) and len(n:=[f'{c.outputpath}/{c.model.data(i)}' for i in d.selectedIndexes()])==1:
            WriteDatabase('INSERT OR REPLACE INTO reports VALUES (?,?,?)',*[c.title,n[0].removeprefix(f'{apppath}/{c.config['path']}/'),datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')])
            for i in self.HomePage().history_group.children():
                if i.name==c.title:i.RefreshReports()
            # m=CreateControl(QPushButton,None,0,0,30,30,icon=c.model.itemFromIndex(d.selectedIndexes()[0]).icon())
            # CreateAnimation(m,b'pos',d.viewport().mapTo(self,d.visualRect(d.selectedIndexes()[0]).topLeft()),self.tab_area.SortedTabs()[0].mapTo(self,QPoint(11,3)),CreateMirror(m,self))
            RequestMessage('i',self,'提示','已将结果文件发送到首页的历史记录中')
    @AddWatcher
    def __shortcutshiftdelete(self)->None:
        if (c:=self.__currentembedcmd()) and isinstance(d:=QApplication.focusWidget(),QListView) and (n:=[f'{c.outputpath}/{c.model.data(i)}' for i in d.selectedIndexes()]) and RequestMessage('w',self,'警告',f'是否删除 {len(n)} 个文件？该操作不可恢复！',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            try:
                for i in n:FileOperation('d',i)
                RequestMessage('i',self,'提示','删除完成')
            except:RequestMessage('w',self,'警告','部分文件被占用，删除失败')
    @AddWatcher
    def __movieframechanged(self,event:int)->None:
        n=QIcon(self.movie.currentPixmap())
        for i in self.runninglist:i.tab_title.setIcon(n)
    @AddWatcher
    def __edit_action(self)->None:
        w=FindTopWindow()
        ToolEditor(w,self.tools[FindControlAtPosition(self.tool_menu,QPoint(),ToolItem).name]).exec()
    @AddWatcher
    def __remove_action(self)->None:
        t=FindControlAtPosition(self.tool_menu,QPoint(),ToolItem,HistoryFrame)
        if isinstance(t,HistoryFrame):
            b=FindControlAtPosition(self.tool_menu,QPoint(),QPushButton)
            if RequestMessage('q',self,'提示',f'是否将工具“{t.name}”的结果文件“{b.toolTip()}”从首页移除？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                WriteDatabase('DELETE FROM reports WHERE tool=? AND filename=?',t.name,b.toolTip())
                c=t.reports_area.children()
                CreateAnimationsByParallel(self,[CreateAnimation(i,b'pos',i.pos(),i.pos()-QPoint(40,0)) for i in c[c.index(b)+1:]])
                CloseControl(b)
        elif isinstance(t.parent(),HistoryFrame):
            if RequestMessage('q',self,'提示',f'是否删除工具“{t.name}”的使用记录？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                self.SaveHistory(3,t.name)
                self.HomePage().RefreshHistory()
        elif RequestMessage('q',self,'提示',f'是否从收藏列表移除工具“{t.name}”？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            appconfig['favorite'].remove(t.name)
            self.SaveConfig()
            self.HomePage().RefreshFavorite()
    @AddWatcher
    def __favorite_action(self)->None:
        w=FindTopWindow()
        t=FindControlAtPosition(self.tool_menu,QPoint(),ToolItem)
        h=self.HomePage()
        if t.name in appconfig['favorite']:RequestMessage('i',self,'提示',f'工具“{t.name}”已经添加到收藏列表，不要重复添加')
        elif RequestMessage('q',self,'提示',f'是否将工具“{t.name}”添加到工具收藏？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            appconfig['favorite'].append(t.name)
            self.SaveConfig()
            self.HomePage().RefreshFavorite()
            if w is self:CreateAnimation(h.favorite_group.children()[-1],b'pos',t.mapTo(h,QPoint()),h.favorite_group.mapTo(h,QPoint(10,15)),CreateMirror(h.favorite_group.children()[-1],h),True)
    @AddWatcher
    def closeEvent(self,event:QCloseEvent)->None:
        if self.pausedtool or self.runninglist:
            match RequestMessage('q',self,'提示','有正在执行的任务，是否释放对应的窗口？\n└是：将正在运行的窗口释放回桌面；\n└否：直接关闭所有窗口；\n└取消：不进行任何操作。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel):
                case QMessageBox.StandardButton.Yes:self.tab_area.CleanUp(2)
                case QMessageBox.StandardButton.No:self.tab_area.CleanUp(3)
                case QMessageBox.StandardButton.Cancel:return event.ignore()
        else:self.tab_area.CleanUp(3)
        if self.processdialog:self.processdialog.close()
        WriteDatabase('VACUUM')
        FileOperation('x','resources/pyvenv.cfg','pyvenv.cfg')
        return super().closeEvent(event)
    @AddWatcher
    def dragEnterEvent(self,event:QDragEnterEvent)->None:
        if event.mimeData().urls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
    @AddWatcher
    def dropEvent(self,event:QDropEvent)->None:
        if (u:=event.mimeData().urls()) and (c:=self.__currentembedcmd()):
            n=c.command_text
            n.setText(f'{n.text().strip()} {u[0].toLocalFile()}')
            n.setFocus()
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        self.tab_area.ArrangeTabs(True)
        return super().resizeEvent(event)
    @AddWatcher
    def timerEvent(self,event:QTimerEvent)->None:
        s=[i.pid for i in psutil.process_iter(['pid','name']) if i.name() in ('cmd.exe','conhost.exe')]
        n=len(appconfig['residual'])
        appconfig['residual']=[i for i in appconfig['residual'] if i[1] in s]
        if len(appconfig['residual'])!=n:self.SaveConfig()
        self.processlist=[i for i in self.processlist if i[1] in s]
        self.pausedtool=False
        self.runninglist.clear()
        for i in self.tab_area.SortedTabs()[1:]:
            if isinstance(i.topic,EmbedCmdTopic):
                p=i.topic.GetProcessList()
                try:
                    if p[0].status()==psutil.STATUS_RUNNING:
                        self.runninglist.append(i)
                        ChangeIcon(i.topic.pause_resume,self.icons['pause'])
                    else:
                        self.pausedtool=True
                        i.tab_title.setIcon(self.icons['pause'])
                        ChangeIcon(i.topic.pause_resume,self.icons['play'])
                except:
                    i.tab_title.setIcon(self.icons['stopped' if i.topic.GetProcessList() is None else 'finished'])
                    ChangeIcon(i.topic.pause_resume,self.icons['stopped'])
        if appconfig['general']['preview']:self.preview_window.Refresh()
        return super().timerEvent(event)

class PreviewWindow(QLabel):
    @AddWatcher
    def __init__(self,parent:QWidget)->None:
        super().__init__(parent)
        self.owner=None
        self.position=QPoint()
        self.previewwidth=0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
        self.setGeometry(-1,-1,1,1)
        self.setStyleSheet('PreviewWindow{background-color:rgba(128,128,128,0.9);border-radius:4px;}')
        self.preview_command=CreateControl(QLabel,self,3,1,0,0)
        self.preview_window=CreateControl(QLabel,self,0,0,0,0)
    @AddWatcher
    def Refresh(self)->None:
        if self.owner:
            c=self.owner.GrabCommand() if appconfig['general']['preview']==2 else []
            w=self.owner.GrabWindow()
            h=len(c)*15
            a,b=self.previewwidth+6,self.previewwidth*w.height()//w.width()+h+6
            self.setGeometry(max(min(self.position.x(),mainwindow.width()-a-5),5),max(min(self.position.y(),mainwindow.height()-b-5),5),a,b)
            self.preview_command.resize(self.previewwidth,h)
            self.preview_command.setText('\n'.join(c))
            self.preview_window.setGeometry(3,h+2,a-6,b-h-6)
            self.preview_window.setPixmap(PixmapTranslucent(w.scaled(self.previewwidth,self.previewwidth*w.height()//w.width(),mode=Qt.TransformationMode.SmoothTransformation),224))
        elif self.width():
            self.setGeometry(-1,-1,1,1)
            self.setPixmap(QPixmap())
    @AddWatcher
    def SetOwner(self,owner:'EmbedCmdTopic|None'=None,position:QPoint=QPoint())->None:
        self.owner=owner
        self.position=position
        self.previewwidth=appconfig['general']['preview']*300
        self.Refresh()

class TopicBase(QFrame):
    @AddWatcher
    def __init__(self,title:str)->None:
        super().__init__()
        self.title=title
        self.resize(1000,500)
    @AddWatcher
    def CleanUp(self,cleancode:int)->bool:
        return True

class TabArea(QWidget):
    @AddWatcher
    def __init__(self,parent:QWidget,width:int,height:int)->None:
        super().__init__(parent)
        self.current=-1
        self.history=[]
        self.pen=QPen(Qt.GlobalColor.gray,1,Qt.PenStyle.SolidLine)
        self.static=False
        self.setGeometry(10,10,width,height)
        self.tab_canvas=QWidget()
        self.tab_canvas.dropEvent=self.__tab_canvas_drop
        AllowDrag(self.tab_canvas,Qt.DropAction.MoveAction,TabItem)
        self.tab_scroll=CreateControl(QScrollArea,self,0,0,width-30,40)
        self.tab_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tab_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tab_scroll.setWidget(self.tab_canvas)
        self.tab_scroll.viewport().setStyleSheet('background-color:transparent;')
        self.new_tab=CreateControl(QPushButton,self,0,0,30,30,'＋',self.__new_tab)
        self.hide_window=CreateControl(QWidget,self,0,40,1,1)
        self.topic_area=CreateControl(QWidget,self,0,40,width,height-40)
        self.anchors=[[6,self.tab_scroll],[8,self.topic_area]]
    @AddWatcher
    def AddTopic(self,topic:TopicBase,icon:QIcon|None=None)->None:
        self.SwitchTab(t:=TabItem(self,topic,icon))
        self.ArrangeTabs(True)
        topic.resize(self.width(),self.height()-40)
        if len(self.tab_canvas.children())>1:t.tab_title.installEventFilter(self)
    @AddWatcher
    def ArrangeTabs(self,withanimation:bool)->None:
        n=0
        t=self.SortedTabs()
        a=[]
        for i,j in enumerate(t):
            j.SetTabTitle(j.topic.title,i)
            if withanimation:a.append(CreateAnimation(j,b'pos',j.pos(),QPoint(n,0)))
            else:j.move(n,0)
            n+=j.width()+3
        self.tab_canvas.resize(n,40)
        self.new_tab.move(min(n,self.width()-30),0)
        if withanimation:CreateAnimationsByParallel(self,a,self.__keepinviewport)
        else:self.__keepinviewport()
    @AddWatcher
    def CleanUp(self,cleancode:int)->None:
        for i in self.SortedTabs()[1:]:i.topic.CleanUp(cleancode)
    @AddWatcher
    def CurrentTab(self)->'TabItem|None':
        return self.SortedTabs()[self.current] if self.current>-1 else None
    @AddWatcher
    def RemoveTab(self,tab:'TabItem')->None:
        if tab.topic.CleanUp(1):
            if tab in self.history:self.history.remove(tab)
            mainwindow.runninglist=[i for i in mainwindow.runninglist if i is not tab]
            CloseControl(tab)
            CloseControl(tab.topic)
            self.SwitchTab(self.history[-1])
            self.ArrangeTabs(True)
    @AddWatcher
    def SwitchIndex(self,index:int=-2)->None:
        if index>-2:self.SwitchTab(self.SortedTabs()[index] if index>-1 else None)
        else:self.repaint()
    @AddWatcher
    def SwitchTab(self,tab:'TabItem|None'=None)->None:
        if tab:
            self.current=self.SortedTabs().index(tab)
            for i in self.tab_canvas.children():MoveControl(i.topic,self.topic_area if i is tab else self.hide_window)
            if tab in self.history:self.history.remove(tab)
            self.history.append(tab)
            self.__keepinviewport()
        else:
            self.current=-1
            self.repaint()
    @AddWatcher
    def SortedTabs(self)->list['TabItem']:
        return sorted(self.tab_canvas.children(),key=lambda i:i.x()+i.width()/2+isinstance(i.topic,EmbedCmdTopic)*1000)
    @AddWatcher
    def __keepinviewport(self)->None:
        if self.current>-1:self.tab_scroll.ensureWidgetVisible(self.CurrentTab(),xmargin=20)
        self.repaint()
    @AddWatcher
    def __new_tab(self)->None:
        ToolsPanel().exec()
    @AddWatcher
    def __tab_canvas_drop(self,event:QDropEvent)->None:
        if isinstance(s:=event.source(),TabItem):
            t=self.SortedTabs()
            c=t[self.current]
            p={i:i.x() for i in t}
            s.move(event.position().x()-s.width()//2,0)
            self.SwitchTab(c)
            self.ArrangeTabs(False)
            t=self.SortedTabs()
            q={i:i.x() for i in t}
            CreateAnimationsByParallel(self,[CreateAnimation(i,b'pos',QPoint(event.position().x()-s.width()//2 if i is s else p[i],0),QPoint(q[i],0)) for i in t[1:]],self.__keepinviewport)
    @AddWatcher
    def eventFilter(self,watched:QObject,event:QEvent)->None:
        match event.type():
            case QEvent.Type.MouseButtonPress:self.static=True
            case QEvent.Type.MouseButtonRelease:return not self.static
            case QEvent.Type.MouseMove:
                if self.static:
                    self.static=False
                    StartDrag(watched.parent(),True)
                    return True
        return super().eventFilter(watched,event)
    @AddWatcher
    def paintEvent(self,event:QPaintEvent)->None:
        w,h=self.width(),self.height()
        t=self.SortedTabs()
        p=QPainter()
        p.begin(self)
        p.setPen(self.pen)
        p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        if t:
            for i,j in enumerate(t):
                b=j.GetBorder()
                if i==self.current:p.drawPolyline([QPoint(1,39),QPoint(b[0]+1,39),QPoint(b[0]+1,j.y()+1),QPoint(b[1],j.y()+1),QPoint(b[1],39),QPoint(w-2,39)])
                else:p.drawRect(b[0]+1,1,b[1]-b[0]-1,34)
        else:p.drawLine(1,39,w-1,39)
        p.drawPolyline([QPoint(w-1,39),QPoint(w-1,h-2),QPoint(1,h-2),QPoint(1,39)])
        p.end()
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        for i in self.SortedTabs():i.topic.resize(self.width(),self.height()-40)
        self.__keepinviewport()
        return super().resizeEvent(event)
    @AddWatcher
    def wheelEvent(self,event:QWheelEvent)->None:
        if event.position().y()<40 and (n:=len(self.SortedTabs())) and (d:=event.angleDelta().y()):self.SwitchIndex(max(min(self.current-d//abs(d),n-1),0))
        return super().wheelEvent(event)

class TabItem(QWidget):
    @AddWatcher
    def __init__(self,owner:TabArea,topic:'HomeTopic|EmbedCmdTopic',icon:QIcon|None=None)->None:
        super().__init__(owner.tab_canvas)
        b=isinstance(topic,EmbedCmdTopic)
        c=owner.history[-1] if owner.history else None
        self.owner=owner
        self.text=''
        self.topic=topic
        self.setGeometry(c.x()+c.width()+3 if c else 0,40,b*20+10,36)
        self.tab_title=CreateControl(QPushButton,self,5,0,0,36,click=self.__tab_title,icon=icon)
        self.tab_title.setStyleSheet('border:none;')
        self.anchors=[[6,self.tab_title]]
        if b:
            self.close_self=CreateControl(QToolButton,self,2,5,25,25,click=self.__close_self)
            self.close_self.setAutoRaise(True)
            self.close_self.setStyleSheet('background-color:none;padding:0px;')
            self.close_self.setText('❌')
            self.anchors.append([3,self.close_self])
        MoveControl(topic,owner.hide_window)
        self.show()
    @AddWatcher
    def GetBorder(self)->tuple[int]:
        b=self.mapTo(self.owner,QPoint()).x()
        return b,b+self.width()
    @AddWatcher
    def SetTabTitle(self,text:str,index:int=-1)->None:
        t=f'{f'&{(index+1)%10}.' if index<10 else ''}{text.replace('&','&&')}'
        self.resize(WidthByPixels(t)+isinstance(self.topic,EmbedCmdTopic)*40+10,36)
        self.tab_title.setText(t)
    @AddWatcher
    def __tab_title(self)->None:
        self.owner.SwitchTab(self)
    @AddWatcher
    def __close_self(self)->None:
        self.owner.RemoveTab(self)
    @AddWatcher
    def enterEvent(self,event:QEnterEvent)->None:
        if appconfig['general']['preview']:mainwindow.preview_window.SetOwner(self.topic if isinstance(self.topic,EmbedCmdTopic) else None,self.mapTo(mainwindow,QPoint(self.width()//2-appconfig['general']['preview']*150-2,45)))
        else:self.owner.SwitchTab(self)
    @AddWatcher
    def leaveEvent(self,event:QEvent)->None:
        if appconfig['general']['preview']:mainwindow.preview_window.SetOwner()
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        return super().resizeEvent(event)

class HomeTopic(TopicBase):
    @AddWatcher
    def __init__(self)->None:
        super().__init__('首页')
        self.static=False
        CreateControl(QWebEngineView,self,11,11,1,1)
        CreateControl(QPushButton,self,10,10,90,30,'工具管理',self.__tools_manager)
        CreateControl(QPushButton,self,110,10,90,30,'进程管理',self.__process_manager)
        CreateControl(QPushButton,self,210,10,90,30,'系统配置',self.__set_config)
        CreateControl(QPushButton,self,310,10,90,30,'文档查看',self.__show_help)
        self.history_most=CreateControl(QPushButton,self,800,10,90,30,'最常使用',self.__buttons)
        self.history_recent=CreateControl(QPushButton,self,900,10,90,30,'最近使用',self.__buttons)
        self.content_canvas=QWidget()
        self.content_scroll=CreateControl(QScrollArea,self,10,50,980,440)
        self.content_scroll.setWidget(self.content_canvas)
        self.favorite_group=CreateControl(QGroupBox,self.content_canvas,0,5,0,0,'工具收藏')
        self.favorite_group.dropEvent=self.__favorite_group_drop
        AllowDrag(self.favorite_group,Qt.DropAction.MoveAction,ToolItem)
        self.history_group=CreateControl(QGroupBox,self.content_canvas,0,5,0,0,['最近使用','最常使用'][appconfig['history']['orderbycount']])
        self.anchors=[[3,self.history_most,self.history_recent],[8,self.content_scroll]]
        self.RefreshFavorite()
        self.RefreshHistory()
    @AddWatcher
    def ArrangeItems(self,kind:int=3)->None:
        n=(self.width()-50)//210
        if kind&1:
            f=lambda i:i.x()+round((i.y()-15)/40)*40000
            c=sorted(self.favorite_group.children(),key=f)
            self.favorite_group.resize(self.width()-40,(len(c)+n-1)//n*40+15)
            CreateAnimationsByParallel(self,[CreateAnimation(j,b'pos',j.pos(),QPoint(i%n*210+8,i//n*40+13)) for i,j in enumerate(c)])
        if kind&2:
            f=lambda i:i.x()+i.y()*1000
            c=sorted(self.history_group.children(),key=f)
            self.history_group.setGeometry(0,self.favorite_group.height()+10,self.width()-40,len(c)*40+15)
            CreateAnimationsByParallel(self,[CreateAnimation(j,b'pos',j.pos(),QPoint(8,i*40+13)) for i,j in enumerate(c)])
        self.content_canvas.resize(self.width()-40,self.favorite_group.height()+self.history_group.height()+10)
    @AddWatcher
    def RefreshFavorite(self)->None:
        c=(self.width()-50)//210
        p=self.favorite_group.children()
        q=appconfig['favorite'][::-1]
        m=[i.name for i in p]
        for i in (i for i in p if i.name not in q):CloseControl(i)
        for i in (i for i in q if i not in m):any(i.installEventFilter(self) for i in ToolItem(self.favorite_group,i).findChildren(QPushButton,options=Qt.FindChildOption.FindDirectChildrenOnly))
        self.favorite_group.resize(self.width()-40,(len(q)+c-1)//c*40+15)
        CreateAnimationsByParallel(self,[CreateAnimation(i,b'pos',i.pos(),QPoint(q.index(i.name)%c*210+8,q.index(i.name)//c*40+13)) for i in self.favorite_group.children()])
        self.history_group.move(0,self.favorite_group.height()+10)
        self.content_canvas.resize(self.width()-40,self.favorite_group.height()+self.history_group.height()+10)
    @AddWatcher
    def RefreshHistory(self)->None:
        p=self.history_group.children()
        q=ReadDatabase(f'SELECT name,COUNT(name) c,MAX(runtime) t FROM history GROUP BY name ORDER BY {'c DESC,'*appconfig['history']['orderbycount']}t DESC')[:appconfig['history']['maxshown']]
        m=[i.name for i in p]
        n=[i[0] for i in q]
        a=[]
        for i in (i for i in p if i.name not in n):CloseControl(i)
        for i in (i for i in q if i[0] not in m):HistoryFrame(self,*i)
        self.history_group.resize(self.width()-40,len(q)*40+15)
        for i in self.history_group.children():
            t=n.index(i.name)
            i.RefreshDetail(*q[t][1:])
            i.RefreshReports()
            a.append(CreateAnimation(i,b'pos',i.pos(),QPoint(8,t*40+13)))
        self.content_canvas.resize(self.width()-40,self.favorite_group.height()+self.history_group.height()+10)
        CreateAnimationsByParallel(self,a)
    @AddWatcher
    def __buttons(self)->None:
        if self.history_group.title()!=self.sender().text():
            self.history_group.setTitle(self.sender().text())
            appconfig['history']['orderbycount']=self.sender().text()=='最常使用'
            mainwindow.SaveConfig()
            self.RefreshHistory()
    @AddWatcher
    def __tools_manager(self)->None:
        ToolsManager().exec()
    @AddWatcher
    def __process_manager(self)->None:
        if not mainwindow.processdialog:mainwindow.processdialog=ProcessDialog()
        if mainwindow.processdialog.isMaximized():mainwindow.processdialog.showMaximized()
        else:mainwindow.processdialog.showNormal()
        mainwindow.processdialog.activateWindow()
    @AddWatcher
    def __set_config(self)->None:
        ConfigDialog().exec()
    @AddWatcher
    def __show_help(self)->None:
        if GetExistsFileName('渗透测试工具箱使用手册.docx'):QDesktopServices.openUrl(QUrl(f'file:///{apppath}/渗透测试工具箱使用手册.docx'))
        else:RequestMessage('w',mainwindow,'警告','帮助文档“渗透测试工具箱使用手册.docx”未找到')
    @AddWatcher
    def __favorite_group_drop(self,event:QDropEvent)->None:
        if isinstance(s:=event.source(),ToolItem):
            f=lambda i:i.x()+round((i.y()-15)/40)*40000
            s.move(event.position().toPoint()-QPoint(102,17))
            self.ArrangeItems(1)
            appconfig['favorite']=[i.name for i in sorted(self.favorite_group.children(),key=f,reverse=True)]
            mainwindow.SaveConfig()
    @AddWatcher
    def eventFilter(self,watched:QObject,event:QEvent)->bool:
        match event.type():
            case QEvent.Type.MouseButtonPress:self.static=True
            case QEvent.Type.MouseButtonRelease:return not self.static
            case QEvent.Type.MouseMove:
                if self.static:
                    self.static=False
                    StartDrag(watched.parent())
                    return True
        return super().eventFilter(watched,event)
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        for i in self.history_group.children():i.resize(self.width()-58,34)
        self.ArrangeItems()
        return super().resizeEvent(event)

class HistoryFrame(QFrame):
    @AddWatcher
    def __init__(self,owner:HomeTopic,name:str,count:int,lastaccess:str)->None:
        super().__init__(owner.history_group)
        w=owner.width()
        self.name=name
        self.owner=owner
        self.resize(w-58,34)
        self.setStyleSheet('HistoryFrame:hover{background-color:gray}')
        self.tool_item=ToolItem(self,name)
        if mainwindow.tools[name]['type']!='url':self.add_reports=CreateControl(QPushButton,self,250,2,90,30,'添加结果文件',self.__add_reports)
        self.reports_area=CreateControl(QWidget,self,390,2,400,30)
        self.use_count=CreateControl(QLabel,self,w-350,2,100,30,f'已使用 {count} 次')
        self.use_time=CreateControl(QLabel,self,w-240,2,185,30,f'最近使用：{lastaccess[:19]}')
        self.anchors=[[3,self.use_count,self.use_time]]
        self.RefreshReports()
        self.show()
    @AddWatcher
    def RefreshConfig(self,config:dict)->None:
        self.name=config['name']
        self.tool_item.RefreshConfig(config)
    @AddWatcher
    def RefreshDetail(self,count:int,lastaccess:str)->None:
        self.use_count.setText(f'已使用 {count} 次')
        self.use_time.setText(f'最近使用：{lastaccess[:19]}')
    @AddWatcher
    def RefreshReports(self)->None:
        n=ReadDatabase('SELECT filename FROM reports WHERE tool=? ORDER BY sendtime',self.name)[:-10:-1]
        for i in self.reports_area.children():CloseControl(i)
        for i,j in enumerate(n[:9]):CreateControl(QPushButton,self.reports_area,i*40,0,30,30,'',self.__buttons,j[0],GetFileIcon(j[0])).contextMenuEvent=self.__buttonscontextmenu
        if len(n)>9:CreateControl(QLabel,self.reports_area,360,0,40,30,'···')
    @AddWatcher
    def __buttons(self)->None:
        s=self.sender()
        t=s.toolTip()
        CreateAnimation(s,b'pos',QPoint(s.x(),50),s.pos(),immediately=True)
        if pathlib.Path(f'{mainwindow.tools[self.name]['path']}/{t}').is_file():QDesktopServices.openUrl(QUrl(f'file:///{apppath}/{mainwindow.tools[self.name]['path']}/{t}'))
        else:
            WriteDatabase('DELETE FROM reports WHERE tool=? AND filename=?',self.name,t)
            c=self.reports_area.children()
            CreateAnimationsByParallel(self,[CreateAnimation(i,b'pos',i.pos(),i.pos()-QPoint(40,0)) for i in c[c.index(s)+1:]])
            CloseControl(s)
            RequestMessage('w',mainwindow,'警告',f'结果文件“{t}”不存在，已将其从工具“{self.name}”的历史记录中移除')
    @AddWatcher
    def __buttonscontextmenu(self,event:QContextMenuEvent)->None:
        mainwindow.edit_action.setVisible(False)
        mainwindow.remove_action.setVisible(True)
        mainwindow.favorite_action.setVisible(False)
        mainwindow.tool_menu.exec(event.globalPos())
    @AddWatcher
    def __add_reports(self)->None:
        t=mainwindow.tools[self.name]
        if (n:=RequestFile('files',mainwindow,'批量添加结果文件',f'{t['path']}/{t['output']}',f'已配置的结果文件格式 ({(t['format'] or '*.txt').replace(',',' ')});;所有文件 (*.*)')[0]):
            WriteDatabaseMany('INSERT OR REPLACE INTO reports VALUES (?,?,?)',[[self.name,i.removeprefix(f'{apppath}/{t['path']}/'),datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')] for i in n])
            self.RefreshReports()
            RequestMessage('i',mainwindow,'提示',f'已将 {len(n)} 个结果文件添加到工具“{self.name}”的历史记录中')
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        return super().resizeEvent(event)

class ToolsPanel(QDialog):
    @AddWatcher
    def __init__(self)->None:
        super().__init__(mainwindow,Qt.WindowType.WindowCloseButtonHint|Qt.WindowType.WindowMaximizeButtonHint)
        self.htmlhead='<style>button{font-size:12px;margin:0px;padding:0px;vertical-align:middle;width:200px;height:30px;}.large{width:170px;}.small{width:30px;}button img{display:inline-block;width:15px;height:15px;}pre{white-space:pre-wrap;word-wrap:break-word;}</style>'
        self.htmltail='document.querySelectorAll("button").forEach((i)=>{i.addEventListener("click",()=>{webchannel.Method([i.offsetWidth>100,i.name]);})})'
        self.title='工具列表'
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setMinimumSize(890,600)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle('工具列表')
        QShortcut(QKeySequence('Ctrl+F'),self).activated.connect(self.__shortcutctrlf)
        self.buttongroups=[]
        CreateControl(QPushButton,self,10,10,100,30,'切换检索模式',self.__switch_search)
        CreateControl(QPushButton,self,130,10,80,30,'工具名称',icon=mainwindow.icons['cmd'])
        CreateControl(QLabel,self,210,10,90,30,'启动内嵌cmd窗口')
        CreateControl(QPushButton,self,310,10,30,30,icon=mainwindow.icons['cmd'])
        CreateControl(QLabel,self,340,10,90,30,'启动独立cmd窗口')
        self.show_unmatched=CreateControl(QCheckBox,self,580,10,100,30,'保留未匹配项')
        self.show_unmatched.setChecked(mainwindow.searchkeywords[0])
        self.show_unmatched.checkStateChanged.connect(self.__show_unmatched)
        self.search_tools=CreateControl(QLineEdit,self,680,10,200,30,mainwindow.searchkeywords[1])
        self.search_tools.setPlaceholderText('检索名称和描述')
        self.search_tools.setStyleSheet('padding-left:5px;padding-right:35px;')
        self.search_tools.keyReleaseEvent=self.__search_process_keyrelease
        self.search_tools.textChanged.connect(self.__search_tools_textchanged)
        self.found_count=CreateControl(QLabel,self,850,10,30,30)
        self.found_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.found_count.setStyleSheet('padding-top:9px;padding-right:2px;')
        self.hidden_board=CreateControl(QWidget,self,10,10,1,1)
        self.boards=[CreateControl(QWidget,self,0,50,890,540),CreateControl(QWidget,self.hidden_board,0,50,890,540)]
        self.content_canvas=QWidget()
        self.content_scroll=CreateControl(QScrollArea,self.boards[0],5,0,875,540)
        self.content_scroll.setWidget(self.content_canvas)
        self.buttongroups=[self.__creategroup(i[0]) for i in mainwindow.kinds]
        self.tools_browser=WebArea(self.boards[1],10,0,870,540,f'<h2>请输入条件检索</h2><script>{mainwindow.htmlroot}</script>',self.__js_method_called,lambda:self.search_tools.setFocus())
        self.tools_browser.loadFinished.connect(self.__browserloaded)
        self.anchors=[[3,self.show_unmatched,self.search_tools,self.found_count],[8,self.content_scroll,self.tools_browser]+self.boards]
        self.search_tools.setFocus()
        self.__search()
    @AddWatcher
    def ArrangeGroups(self)->None:
        t=5
        n=(self.width()-50)//210
        a=[]
        for i in self.buttongroups:
            c=[j for j in i.children() if j.matched]
            i.setGeometry(5,t,self.width()-40,(len(c)+n-1)//n*40+15)
            for j,k in enumerate(c):a.append(CreateAnimation(k,b'pos',k.pos(),QPoint(j%n*210+8,j//n*40+13)))
            t+=i.height()+5
        CreateAnimationsByParallel(self,a)
        self.content_canvas.resize(self.width()-35,t-5)
    @AddWatcher
    def CreateButtons(self,config:dict)->str:
        n=GetButtonIconName(config)
        return f'<button class="large" name="{config['name']}"><img src="{n}">{config['name']}</button><button class="small" name="{config['name']}"><img src="{n}"></button>' if config['type']=='cmd' else f'<button name="{config['name']}"><img src="{n}">{config['name']}</button>'
    @AddWatcher
    def RefreshTools(self,name:str,config:dict)->None:
        any(i.RefreshConfig(config) for j in self.buttongroups for i in j.children() if i.name==name)
        self.__search()
    @AddWatcher
    def __browserloaded(self,event:bool)->None:
        self.tools_browser.find_area.show()
        self.tools_browser.find_text.setText(self.search_tools.text())
        self.tools_browser.find_next.click()
    @AddWatcher
    def __creategroup(self,kind:str)->QGroupBox:
        g=CreateControl(QGroupBox,self.content_canvas,0,0,0,0)
        g.setTitle(kind.replace('&','&&'))
        for i in (i for i in mainwindow.programs if i['kind']==kind):ToolItem(g,i['name'],self)
        return g
    @AddWatcher
    def __shortcutctrlf(self)->None:
        self.tools_browser.WebFinderSwitch()
    @AddWatcher
    def __search(self)->None:
        s=self.search_tools.text()
        a=self.show_unmatched.isChecked()
        b=bool(s)
        for i in (i for j in self.buttongroups for i in j.children()):
            c=s.lower() in i.target
            i.matched=(a or c)
            i.setVisible(a or c)
            i.border_frame.setVisible(b and c)
        mainwindow.searchkeywords[1]=s
        self.ArrangeGroups()
        t=[i for i in mainwindow.programs if s.lower() in f'{i['name']}\n{i['note']}'.lower()] if s else []
        self.found_count.setText(str(len(t)) if s else '')
        if self.show_unmatched.isChecked():t=mainwindow.programs
        self.tools_browser.setHtml(f'{self.htmlhead}{''.join(f'{self.CreateButtons(i)}{f'<pre>{i['note']}</pre>'}<hr>' for i in t)}<script>{mainwindow.htmlroot}{self.htmltail}</script>' if t else f'<h2>无匹配项，请修改关键字</h2><script>{mainwindow.htmlroot}</script>' if s else f'<h2>请输入关键字检索</h2><script>{mainwindow.htmlroot}</script>',QUrl(apppath))
    @AddWatcher
    def __switch_search(self)->None:
        n=self.boards.index(self.hidden_board.children()[0])
        MoveControl(self.boards[n],self)
        MoveControl(self.boards[1-n],self.hidden_board)
    @AddWatcher
    def __show_unmatched(self,event:Qt.CheckState)->None:
        mainwindow.searchkeywords[0]=self.show_unmatched.isChecked()
        self.__search()
    @AddWatcher
    def __search_process_keyrelease(self,event:QKeyEvent)->None:
        if event.key() in [Qt.Key.Key_Enter,Qt.Key.Key_Return] and self.hidden_board.children()[0] is self.boards[0]:self.tools_browser.find_text.setFocus()
    @AddWatcher
    def __search_tools_textchanged(self,text:str)->None:
        self.__search()
    @AddWatcher
    def __js_method_called(self,argument:list)->None:
        mainwindow.UseTool(argument[1],argument[0])
        self.done(-1)
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        self.ArrangeGroups()
        return super().resizeEvent(event)

class ToolItem(QFrame):
    @AddWatcher
    def __init__(self,parent:QGroupBox,name:str,panel:ToolsPanel|None=None)->None:
        super().__init__(parent)
        t=mainwindow.tools[name]
        self.matched=True
        self.name=name
        self.panel=panel
        self.target=f'{t['name']}\n{t['note']}'.lower()
        self.resize(204,34)
        self.setStyleSheet('ToolItem:hover{background-color:gray}')
        c=mainwindow.icons.get(t['prefix'] or t['icon']) if (t['path'],t['file'].lower()) in [('.','cmd.exe'),('.','powershell.exe')] or GetExistsFileName(f'{t['path']}/{t['file'].split(' ')[-1]}') else mainwindow.icons['stopped']
        n=t['note'] or t['name']
        if t['type']=='cmd':
            c=c or mainwindow.icons['cmd']
            CreateControl(QPushButton,self,2,2,170,30,t['name'].replace('&','&&'),self.__buttons,n,c)
            CreateControl(QPushButton,self,172,2,30,30,'',self.__buttons,n,c)
        else:CreateControl(QPushButton,self,2,2,200,30,t['name'].replace('&','&&'),self.__buttons,f'{f'{t['path']}\n' if t['type']=='url' else ''}{n}',GetUrlIcon(t['name']) if t['type']=='url' else (c or GetFileIcon(f'{t['path']}/{t['file']}')))
        self.border_frame=CreateControl(QFrame,self,2,2,200,30)
        self.border_frame.hide()
        self.border_frame.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,True)
        self.border_frame.setStyleSheet('border:2px solid red;')
        self.show()
    @AddWatcher
    def RefreshConfig(self,config:dict)->None:
        n=config['name']
        self.name=n
        self.target=f'{n}\n{config['note']}'.lower()
        self.children()[0].setText(n.replace('&','&&'))
        for i in self.children()[:(config['type']=='cmd')+1]:ChangeIcon(i,GetUrlIcon(config['name']) if config['type']=='url' else mainwindow.icons.get(config['prefix'] or config['icon']) or (mainwindow.icons['cmd'] if config['type']=='cmd' else GetFileIcon(f'{config['path']}/{config['file']}'))).setToolTip(config['note'] or n)
    @AddWatcher
    def __buttons(self)->None:
        s=self.sender()
        mainwindow.UseTool(self.name,s.text())
        if self.panel:self.panel.done(-1)
        else:CreateAnimation(s,b'pos',QPoint(s.x(),50),s.pos(),immediately=True)
    @AddWatcher
    def contextMenuEvent(self,event:QContextMenuEvent)->None:
        mainwindow.edit_action.setVisible(True)
        mainwindow.remove_action.setVisible(not self.panel)
        mainwindow.favorite_action.setVisible(self.parent() is not mainwindow.HomePage().favorite_group)
        mainwindow.tool_menu.exec(self.mapToGlobal(QPoint(max(min(event.pos().x(),100),5),max(min(event.pos().y(),15),5))))
        if isValid(self):
            QApplication.sendEvent(self,QEvent(QEvent.Type.HoverLeave))
            if isinstance(self.parent(),HistoryFrame):QApplication.sendEvent(self.parent(),QEvent(QEvent.Type.HoverLeave))

class ToolsManager(QDialog):
    @AddWatcher
    def __init__(self)->None:
        super().__init__(mainwindow,Qt.WindowType.WindowCloseButtonHint)
        self.model=QStringListModel()
        self.static=False
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setFixedSize(260,410)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle('工具管理器')
        self.hidden_manager=CreateControl(QWidget,self,10,10,1,1)
        self.managers=[ScrollableGroup(self,10,10,240,350,'自建工具管理'),ScrollableGroup(self.hidden_manager,10,10,240,350,'工具分类管理')]
        self.managers[1].content_canvas.dropEvent=self.__kind_grou_drop
        self.kind_seperator=CreateControl(QFrame,self.managers[1].content_canvas,8,0,198,5)
        self.kind_seperator.setStyleSheet('background-color:gray;')
        self.switch_manager=CreateControl(QPushButton,self,10,370,120,30,'切换到分类管理',self.__switch_manager)
        self.add_item=CreateControl(QPushButton,self,170,370,80,30,'添加工具',self.__add_item)
        AllowDrag(self.managers[1].content_canvas,Qt.DropAction.MoveAction,ManagerItem)
        self.RefreshTools()
        self.RefreshKinds()
    @AddWatcher
    def ArrangeItems(self)->None:
        n=sorted(self.managers[1].content_canvas.findChildren(ManagerItem,options=Qt.FindChildOption.FindDirectChildrenOnly),key=lambda i:i.kind*10000+i.y())
        CreateAnimationsByParallel(self,[CreateAnimation(j,b'pos',j.pos(),QPoint(5,i*40+j.kind*20-20)) for i,j in enumerate(n)])
        self.kind_seperator.move(8,len([i for i in n if i.kind==1])*40+5)
    @AddWatcher
    def RefreshKinds(self,name:str='',config:dict|None=None)->None:
        if name:return any(i.RefreshConfig(config) for i in self.managers[1].content_canvas.findChildren(ManagerItem,options=Qt.FindChildOption.FindDirectChildrenOnly) if i.name==name)
        p=self.managers[1].content_canvas.findChildren(ManagerItem,options=Qt.FindChildOption.FindDirectChildrenOnly)
        q=mainwindow.kinds
        m=[i.name for i in p]
        n=[i[0] for i in q]
        for i in (i for i in p if i.name not in n):CloseControl(i)
        for i in (i for i in q if i[0] not in m):any(i.installEventFilter(self) for i in ManagerItem(self,self.managers[1],i[1],i[0]).children())
        self.managers[1].content_canvas.resize(212,len(self.managers[1].content_canvas.children())*40-22)
        d={i.name:i for i in self.managers[1].content_canvas.findChildren(ManagerItem,options=Qt.FindChildOption.FindDirectChildrenOnly)}
        CreateAnimationsByParallel(self,[CreateAnimation(d[j[0]],b'pos',d[j[0]].pos(),QPoint(5,i*40+j[1]*20-20)) for i,j in enumerate(q)]+[CreateAnimation(self.kind_seperator,b'pos',self.kind_seperator.pos(),QPoint(8,len([i for i in q if i[1]==1])*40+5))])
    @AddWatcher
    def RefreshTools(self,name:str='',config:dict|None=None)->None:
        if name:return any(i.RefreshConfig(config) for i in self.managers[0].content_canvas.children() if i.name==name)
        p=self.managers[0].content_canvas.children()
        q=[i for i in mainwindow.programs if i['extra']]
        m=[i.name for i in p]
        n=[i['name'] for i in q]
        for i in (i for i in p if i.name not in n):CloseControl(i)
        for i in (i for i in n if i not in m):ManagerItem(self,self.managers[0],0,i)
        self.managers[0].content_canvas.resize(212,len(self.managers[0].content_canvas.children())*40-3)
        CreateAnimationsByParallel(self,[CreateAnimation(j,b'pos',j.pos(),QPoint(5,i*40)) for i,j in enumerate(self.managers[0].content_canvas.children())])
    @AddWatcher
    def __switch_manager(self)->None:
        n=self.managers.index(self.hidden_manager.children()[0])
        self.switch_manager.setText(f'切换到{['分类','工具'][n]}管理')
        self.add_item.setText(f'添加{['工具','分类'][n]}')
        MoveControl(self.managers[n],self)
        MoveControl(self.managers[1-n],self.hidden_manager)
    @AddWatcher
    def __add_item(self)->None:
        [KindEditor,ToolEditor][self.managers.index(self.hidden_manager.children()[0])](self).exec()
    @AddWatcher
    def __kind_grou_drop(self,event:QDropEvent)->None:
        if isinstance(s:=event.source(),ManagerItem):
            s.move(event.position().toPoint()-QPoint(102,17))
            self.ArrangeItems()
            mainwindow.kinds=[[i.name,i.kind] for i in sorted(self.managers[1].content_canvas.findChildren(ManagerItem,options=Qt.FindChildOption.FindDirectChildrenOnly),key=lambda i:i.kind*10000+i.y())]
            mainwindow.SaveKinds()
    @AddWatcher
    def eventFilter(self,watched:QObject,event:QEvent)->bool:
        match event.type():
            case QEvent.Type.MouseButtonPress:self.static=True
            case QEvent.Type.MouseButtonRelease:return not self.static
            case QEvent.Type.MouseMove:
                if self.static:
                    self.static=False
                    StartDrag(watched.parent())
                    return True
        return super().eventFilter(watched,event)

class ManagerItem(QFrame):
    @AddWatcher
    def __init__(self,owner:ToolsManager,parent:ScrollableGroup,kind:int,name:str)->None:
        super().__init__(parent.content_canvas)
        self.kind=kind
        self.name=name
        self.owner=owner
        self.setGeometry(8,0,204,34)
        self.setStyleSheet('ManagerItem:hover{background-color:gray}')
        self.edit_item=CreateControl(QPushButton,self,2,2,200,30,name.replace('&','&&'),self.__edit_item)
        self.edit_item.setStyleSheet('padding-right:20px;')
        self.delete_item=CreateControl(QToolButton,self,177,7,20,20,click=self.__delete_item)
        self.delete_item.setAutoRaise(True)
        self.delete_item.setText('❌')
        self.show()
    @AddWatcher
    def RefreshConfig(self,config:dict)->None:
        self.name=config['name']
        self.edit_item.setText(config['name'].replace('&','&&'))
    @AddWatcher
    def __edit_item(self)->None:
        if self.kind:KindEditor(self.owner,[self.name,self.kind]).exec()
        else:ToolEditor(self.owner,mainwindow.tools[self.name]).exec()
    @AddWatcher
    def __delete_item(self)->None:
        if self.kind:
            if next((i for i in mainwindow.programs if i['kind']==self.name),None):return RequestMessage('w',self.owner,'警告','不能删除非空的分类')
            if RequestMessage('w',self.owner,'警告',f'是否将分类“{self.name}”从工具箱删除？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                mainwindow.kinds=[i for i in mainwindow.kinds if i[0]!=self.name]
                mainwindow.SaveKinds()
                self.owner.RefreshKinds()
                RequestMessage('i',self.owner,'提示',f'分类“{self.name}”已删除')
        else:
            t=mainwindow.tools[self.name]
            if mainwindow.CheckProcess(self.name):return RequestMessage('w',self.owner,'警告','不能移除正在运行的命令行工具')
            if RequestMessage('w',self.owner,'警告',f'是否将自建工具“{self.name}”从工具箱移除？\n移除后将保留工具程序目录，但会删除帮助文档和关联图标。\n如要再次使用，需重新添加。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                if t['type']=='cmd':FileOperation('d',f'resources/docs/{self.name}.html')
                if t['type']=='url':FileOperation('d',f'resources/shortcuts/{self.name}.ico')
                mainwindow.SaveTools(3,{'name':self.name})
                mainwindow.HomePage().RefreshFavorite()
                mainwindow.HomePage().RefreshHistory()
                self.owner.RefreshTools()
                RequestMessage('i',self.owner,'提示',f'工具“{self.name}”已移除')

class ToolEditor(QDialog):
    @AddWatcher
    def __init__(self,owner:MainWindow|ToolsPanel|ToolsManager,config:dict|None=None)->None:
        super().__init__(owner,Qt.WindowType.WindowCloseButtonHint)
        a=mainwindow.CheckProcess(config['name']) if config else False
        b=bool(config and not config['extra'])
        self.config=config
        self.iconlocal=self.iconurl=''
        self.kinds=[[i[0] for i in mainwindow.kinds if i[1]==1],[i[0] for i in mainwindow.kinds if i[1]==2]]
        self.model=QStringListModel()
        self.model.setStringList(self.kinds[0])
        self.owner=owner
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setFixedSize(400,485)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle(f'工具{'编辑' if config else '添加'}')
        CreateControl(QLabel,self,10,10,50,25,'工具来源')
        self.source_value=CreateControl(QLabel,self,70,10,320,25,['自建','内置（非必要不建议修改元数据）'][b])
        self.source_value.setStyleSheet(f'color:{['green','red'][b]};')
        CreateControl(QLabel,self,10,45,50,25,'工具名称')
        self.name_value=CreateControl(QLineEdit,self,70,45,320,25)
        CreateControl(QLabel,self,10,80,50,25,'工具类型')
        self.type_value=CreateControl(QComboBox,self,70,80,320,25)
        self.type_value.addItems(['命令行工具','界面工具','在线工具'])
        self.type_value.currentIndexChanged.connect(self.__type_value)
        CreateControl(QLabel,self,10,115,50,25,'功能分类')
        self.kind_value=CreateControl(QComboBox,self,70,115,320,25)
        self.kind_value.setModel(self.model)
        CreateControl(QLabel,self,10,175,50,25,'备注信息')
        self.note_value=CreateControl(QTextEdit,self,70,150,320,75)
        self.local_board=CreateControl(QWidget,self,10,235,380,200)
        CreateControl(QLabel,self.local_board,0,0,50,25,'运行方式')
        self.prefix_value=CreateControl(QComboBox,self.local_board,60,0,320,25)
        self.prefix_value.addItems(['可执行程序','java','java8','java9+','python'])
        self.prefix_value.currentIndexChanged.connect(self.__prefix_value)
        CreateControl(QLabel,self.local_board,0,35,50,25,'程序路径')
        self.path_value=CreateControl(QLineEdit,self.local_board,60,35,260,25)
        self.path_value.setReadOnly(True)
        self.path_value.setStyleSheet('padding-right:24px;')
        self.path_value.textChanged.connect(self.__path_file_changed)
        self.path_icon=CreateControl(QPushButton,self.local_board,295,35,26,26,click=self.__path_icon,icon=GetFileIcon(apppath))
        self.select_file=CreateControl(QPushButton,self.local_board,330,35,50,60,'选择\n程序\n文件',self.__select_file)
        CreateControl(QLabel,self.local_board,0,70,50,25,'程序文件')
        self.file_value=CreateControl(QLineEdit,self.local_board,60,70,260,25)
        self.file_value.setReadOnly(True)
        self.file_value.setStyleSheet('padding-right:24px;')
        self.file_value.textChanged.connect(self.__path_file_changed)
        self.file_icon=CreateControl(QPushButton,self.local_board,295,70,26,26,click=self.__file_icon)
        self.url_board=CreateControl(QWidget,self,10,235,380,60)
        self.url_board.hide()
        CreateControl(QLabel,self.url_board,0,0,50,25,'工具地址')
        self.url_value=CreateControl(QLineEdit,self.url_board,60,0,320,25)
        self.url_value.setStyleSheet('padding-right:24px;')
        self.url_icon=CreateControl(QPushButton,self.url_board,355,0,26,26,click=self.__url_icon)
        CreateControl(QLabel,self.url_board,0,35,50,25,'浏 览 器')
        self.browser_value=CreateControl(QLineEdit,self.url_board,60,35,320,25)
        self.browser_value.setPlaceholderText('点击后按退格键或删除键以清空内容')
        self.browser_value.setReadOnly(True)
        self.browser_value.setStyleSheet('padding-right:24px;')
        self.browser_value.keyPressEvent=self.__value_keypress
        self.browser_value.textChanged.connect(self.__path_file_changed)
        self.browser_icon=CreateControl(QPushButton,self.url_board,355,35,26,26,click=self.__browser_icon)
        self.output_board=CreateControl(QWidget,self,10,340,380,95)
        CreateControl(QLabel,self.output_board,0,0,50,25,'输出目录')
        self.output_value=CreateControl(QLineEdit,self.output_board,60,0,260,25)
        self.output_value.setReadOnly(True)
        self.output_value.textChanged.connect(self.__output_format_changed)
        self.select_output=CreateControl(QPushButton,self.output_board,330,0,50,60,'选择\n结果\n文件',self.__select_output)
        CreateControl(QLabel,self.output_board,0,35,50,25,'输出格式')
        self.format_value=CreateControl(QLineEdit,self.output_board,60,35,260,25)
        self.format_value.setPlaceholderText('默认*.txt')
        self.format_value.textChanged.connect(self.__output_format_changed)
        self.icons_board=CreateControl(QWidget,self.output_board,320,35,0,26)
        CreateControl(QLabel,self.output_board,0,70,50,25,'帮助文档')
        self.help_value=CreateControl(QLineEdit,self.output_board,60,70,260,25)
        self.help_value.setPlaceholderText('点击后按退格键或删除键以清空内容')
        self.help_value.setReadOnly(True)
        self.help_value.keyPressEvent=self.__value_keypress
        self.select_help=CreateControl(QPushButton,self.output_board,330,70,50,25,'文档',self.__select_help)
        self.edit_ok=CreateControl(QPushButton,self,10,445,90,30,'运行中' if a else '确定',self.__edit_ok)
        if a:self.edit_ok.setEnabled(False)
        self.edit_cancel=CreateControl(QPushButton,self,300,445,90,30,'取消',self.__edit_cancel)
        if config:
            self.name_value.setText(config['name'])
            self.type_value.setCurrentText({'cmd':'命令行工具','ui':'界面工具','url':'在线工具'}[config['type']])
            self.type_value.setEnabled(False)
            self.kind_value.setCurrentText(config['kind'])
            self.prefix_value.setCurrentText(config['prefix'])
            self.note_value.setText(config['note'])
            if config['type']=='url':
                self.url_value.setText(config['path'])
                self.url_icon.setIcon(GetUrlIcon(config['name']))
                self.browser_value.setText(config['file'])
                self.browser_icon.setIcon(mainwindow.icons['edge'])
            else:
                self.iconlocal=config['icon']
                self.path_value.setText(config['path'])
                self.file_value.setText(config['file'])
            self.output_value.setText(config['output'])
            self.format_value.setText(config['format'])
            self.help_value.setText(GetExistsFileName(f'{apppath}/resources/docs/{config['name']}.html'))
            self.startTimer(1000)
        self.__refreshicon()
        self.__refreshicons()
    @AddWatcher
    def UseIcon(self,icon:str)->None:
        if self.type_value.currentText()=='在线工具':self.iconurl=icon
        else:self.iconlocal=icon
        self.__refreshicon()
    @AddWatcher
    def __refreshicon(self)->None:
        if self.type_value.currentText()=='在线工具':
            self.url_icon.setIcon(QIcon(self.iconurl) if self.iconurl else GetUrlIcon(self.config['name']) if self.config else mainwindow.icons['edge'])
            self.browser_icon.setIcon(GetFileIcon(self.browser_value.text()) if self.browser_value.text() else mainwindow.icons['edge'])
        else:
            p=pathlib.Path(f'{self.path_value.text() or '.'}/{self.file_value.text()}')
            t=self.prefix_value.currentText()
            self.file_icon.setIcon(mainwindow.icons[self.iconlocal] if self.iconlocal else mainwindow.icons[t] if self.prefix_value.currentIndex() else mainwindow.icons['cmd'] if not self.type_value.currentIndex() else GetFileIcon(p) if p.is_file() else QIcon())
    @AddWatcher
    def __refreshicons(self)->None:
        n=sorted({f'*.{i.split('.')[-1].lower()}' for i in self.format_value.text().split(',') if '.' in i})[:5]
        for i in self.icons_board.children():CloseControl(i)
        self.format_value.setStyleSheet(f'padding-right:{len(n)*25-1}px;')
        self.icons_board.setGeometry(320-len(n)*25,35,len(n)*25,26)
        for i,j in enumerate(n):CreateControl(QPushButton,self.icons_board,i*25,0,26,26,icon=GetFileIcon(j))
    @AddWatcher
    def __type_value(self,index:int)->None:
        self.model.setStringList(self.kinds[index==2])
        self.local_board.setVisible(index<2)
        self.url_board.setVisible(index==2)
        self.output_board.setVisible(index<2)
        self.output_board.resize(380,95-bool(index)*35)
        self.help_value.setEnabled(not index)
        self.__refreshicon()
    @AddWatcher
    def __select_file(self)->None:
        if (n:=RequestFile('file',self,'选择程序文件',apppath)[0].removeprefix(f'{apppath}/')):
            if ':' in n:RequestMessage('w',self,'警告','不能将工具箱目录外部的程序添加到工具箱')
            else:
                m=n.split('/')
                self.path_value.setText('/'.join(m[:-1]) or '.')
                self.file_value.setText(m[-1])
                if self.type_value.currentText()=='命令行工具':self.output_value.setText('')
    @AddWatcher
    def __prefix_value(self,index:int)->None:
        self.__refreshicon()
    @AddWatcher
    def __path_icon(self)->None:
        if self.path_value.text():QDesktopServices.openUrl(QUrl.fromLocalFile(QDir.toNativeSeparators(self.path_value.text())))
    @AddWatcher
    def __file_icon(self)->None:
        IconSelector(self,GetFileIcon(f'{self.path_value.text() or '.'}/{self.file_value.text()}'),['cmd','powershell','java','python','edge']).exec()
    @AddWatcher
    def __url_icon(self)->None:
        IconSelector(self,GetUrlIcon(self.config['name']) if self.config else mainwindow.icons['edge']).exec()
    @AddWatcher
    def __browser_icon(self)->None:
        if (n:=RequestFile('file',self,'选择浏览器',apppath,'浏览器 (*.exe)')[0]):
            self.browser_value.setText(n)
            self.browser_icon.setIcon(GetFileIcon(n))
    @AddWatcher
    def __select_output(self)->None:
        if self.file_value.text():
            p=f'{apppath}/{self.path_value.text()}'
            if (n:=RequestFile('files',self,'选择结果文件，支持同时选择最多5种不同格式的文件',p)[0]):
                if ':' in n[0].removeprefix(p):RequestMessage('w',self,'警告','不能将工具目录外部的文件设置为结果文件')
                else:
                    m=GetOutputFormat(p,n)
                    self.output_value.setText(m[0])
                    self.format_value.setText(m[1])
        else:RequestMessage('w',self,'警告','请先配置工具的程序文件')
    @AddWatcher
    def __select_help(self)->None:
        if self.file_value.text():
            if (n:=RequestFile('file',self,'选择帮助文档',apppath,'帮助文档 (*.html)')[0]):self.help_value.setText(n)
        else:RequestMessage('w',self,'警告','请先配置工具的程序文件')
    @AddWatcher
    def __edit_ok(self)->None:
        n=self.config['name'] if self.config else ''
        p=mainwindow.programs
        q={i:'' for i in mainwindow.programkeys}|{'name':self.name_value.text()}|{'extra':not self.config or self.config['extra']}
        if not q['name']:return RequestMessage('w',self,'警告','尚未配置工具名称')
        if ' ' in q['name']:return RequestMessage('w',self,'警告','工具名称不能包含空格')
        q['type']=['cmd','ui','url'][self.type_value.currentIndex()]
        if q['type']=='cmd' and WidthByPixels(q['name'])>138 or WidthByPixels(q['name'])>162:return RequestMessage('w',self,'警告','工具名称太长，请修改：\n命令行工具最长23个半角字符，其他工具最长27个半角字符')
        if any(i['name']==q['name'] for i in p if i is not self.config):return RequestMessage('w',self,'警告','工具名称重复')
        if q['type']=='url':
            q['path']=self.url_value.text()
            if not q['path']:return RequestMessage('w',self,'警告','尚未配置工具 url')
            q['file']=self.browser_value.text()
        else:
            q['path']=self.path_value.text()
            q['file']=self.file_value.text()
            if not q['file']:return RequestMessage('w',self,'警告','尚未配置工具文件名')
            q['icon']=self.iconlocal
        q['kind']=self.kind_value.currentText()
        if self.prefix_value.currentIndex():q['prefix']=self.prefix_value.currentText()
        q['note']=self.note_value.toPlainText()
        if q['type']=='url':
            if self.iconurl:
                if self.iconurl.lower()!=f'{apppath}/resources/shortcuts/{n or q['name']}.ico'.lower():
                    if RequestMessage('q',self,'提示','该操作会将图标文件复制到图标目录，是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.No:return
                    FileOperation('c',self.iconurl,f'resources/shortcuts/{n or q['name']}.ico')
        else:
            if self.output_value.text():q['output']=self.output_value.text()
            if self.format_value.text():q['format']=self.format_value.text()
            if q['type']=='cmd':
                if self.help_value.text():
                    if self.help_value.text().lower()!=f'{apppath}/resources/docs/{n or q['name']}.html'.lower():
                        if RequestMessage('q',self,'提示','该操作会将帮助文档复制到文档目录，是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.No:return
                        FileOperation('c',self.help_value.text(),f'resources/docs/{n or q['name']}.html')
                else:FileOperation('d',f'resources/docs/{n}.html')
        t=f'工具{'编辑' if self.config else '添加'}完成'
        mainwindow.SaveTools(bool(self.config)+1,q|{'oldname':n})
        if self.config:
            self.config.clear()
            self.config.update(q)
        else:p.append(q)
        mainwindow.RefreshTools(n,q)
        if self.owner is not mainwindow:self.owner.RefreshTools(n,q)
        self.done(-1)
        RequestMessage('i',self,'提示',t)
    @AddWatcher
    def __edit_cancel(self)->None:
        self.done(-1)
    @AddWatcher
    def __path_file_changed(self,text:str)->None:
        self.__refreshicon()
        self.__refreshicons()
    @AddWatcher
    def __output_format_changed(self,text:str)->None:
        self.__refreshicons()
    @AddWatcher
    def __value_keypress(self,event:QKeyEvent)->None:
        if event.key() in [Qt.Key.Key_Backspace,Qt.Key.Key_Delete]:(self.browser_value if self.type_value.currentIndex() else self.help_value).setText('')
        else:return self.keyPressEvent(event)
    @AddWatcher
    def timerEvent(self,event:QTimerEvent)->None:
        if mainwindow.CheckProcess(self.config['name']):
            self.edit_ok.setEnabled(False)
            self.edit_ok.setText('运行中')
        else:
            self.edit_ok.setEnabled(True)
            self.edit_ok.setText('确定')
        return super().timerEvent(event)

class IconSelector(QDialog):
    @AddWatcher
    def __init__(self,parent:ToolEditor,icon:QIcon,icons:list[str]|None=None)->None:
        super().__init__(parent,Qt.WindowType.WindowCloseButtonHint)
        self.icons=icons or ['']
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setFixedSize(len(icons)*40+100 if icons else 220,50)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle('图标选择')
        CreateControl(QPushButton,self,10,10,80,30,'自动',self.__buttons,icon=icon)
        if icons:
            for i,j in enumerate(icons):CreateControl(QPushButton,self,i*40+100,10,30,30,click=self.__buttons,icon=mainwindow.icons[j])
        else:
            self.url_icon=CreateControl(QPushButton,self,100,10,30,30,click=self.__buttons,icon=mainwindow.icons['stopped'])
            self.select_file=CreateControl(QPushButton,self,140,10,70,30,'打开文件',self.__select_file)
    @AddWatcher
    def __buttons(self)->None:
        n=self.children().index(self.sender())
        if n==1 and not self.icons[0]:return RequestMessage('w',self,'警告','尚未配置图标文件，无法选择该项')
        self.parent().UseIcon((['']+self.icons)[n])
        self.done(-1)
    @AddWatcher
    def __select_file(self)->None:
        if (n:=RequestFile('file',self,'选择图标文件',apppath,'图标文件 (*.ico)')[0]):
            self.icons=[n]
            self.url_icon.setIcon(QIcon(n))

class KindEditor(QDialog):
    @AddWatcher
    def __init__(self,owner:ToolsManager,config:list|None=None)->None:
        super().__init__(owner,Qt.WindowType.WindowCloseButtonHint)
        self.config=config
        self.owner=owner
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setFixedSize(330,90)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle(f'分类{'编辑' if config else '添加'}')
        self.kind_name=CreateControl(QLineEdit,self,10,10,170,25)
        self.kind_type=RadioButtonGroup(self,190,10,130,25,['本地工具','在线工具'])
        if config:
            self.kind_name.setText(config[0])
            self.kind_type.setEnabled(False)
            self.kind_type.SetValue(config[1]-1)
        self.edit_ok=CreateControl(QPushButton,self,10,50,90,30,'确定',self.__edit_ok)
        self.edit_cancel=CreateControl(QPushButton,self,230,50,90,30,'取消',self.__edit_cancel)
    @AddWatcher
    def __edit_ok(self)->None:
        m,n=self.kind_name.text(),self.kind_type.GetValue()+1
        if not m:return RequestMessage('w',self,'警告','尚未配置分类名称')
        if ' ' in m:return RequestMessage('w',self,'警告','分类名称不能包含空格')
        if WidthByPixels(m)>168:return RequestMessage('w',self,'警告','分类名称太长，请修改')
        if (not self.config or m!=self.config[0]) and any(i[0]==m for i in mainwindow.kinds):return RequestMessage('w',self,'警告','分类名称重复')
        if not n:return RequestMessage('w',self,'警告','尚未配置分类的类型')
        if self.config:
            if RequestMessage('q',self,'提示','是否修改分类名称，并同步到该分类的所有工具？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.No:return
            next(i for i in mainwindow.kinds if i[0]==self.config[0])[0]=m
            for i in (i for i in mainwindow.programs if i['kind']==self.config[0]):i['kind']=m
            mainwindow.tools={i['name']:i for i in mainwindow.programs}
            WriteDatabase('UPDATE tools SET kind=? WHERE kind=?',m,self.config[0])
        else:
            if RequestMessage('q',self,'提示','是否添加新的分类？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.No:return
            mainwindow.kinds=sorted(mainwindow.kinds+[[m,n]],key=lambda i:i[1])
        mainwindow.SaveKinds()
        self.owner.RefreshKinds(self.config[0] if self.config else '',m)
        self.done(-1)
        RequestMessage('i',self,'提示',f'分类{'编辑' if self.config else '添加'}完成')
    @AddWatcher
    def __edit_cancel(self)->None:
        self.done(-1)

class ProcessDialog(QMainWindow):
    @AddWatcher
    def __init__(self)->None:
        super().__init__()
        self.foldlist=[]
        self.model=ProcessTreeModel()
        self.selected=0
        self.move(mainwindow.x()+1335,mainwindow.y())
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setMinimumSize(400,750)
        if appconfig['process']['pintop']:self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True)
        self.setWindowIcon(QIcon('resources/icons/toolbox.ico'))
        self.setWindowTitle('进程管理')
        #QShortcut(QKeySequence('Space'),self).activated.connect(self.__shortcutspace)
        QShortcut(QKeySequence('F5'),self).activated.connect(self.__shortcutf5)
        QShortcut(QKeySequence('F6'),self).activated.connect(self.__shortcutf6)
        QShortcut(QKeySequence('F7'),self).activated.connect(self.__shortcutf7)
        self.process_menu=QMenu(self)
        #self.file_property=self.process_menu.addAction('查看文件属性','Space',self.__shortcutspace)
        self.view_file=self.process_menu.addAction('打开文件位置','F5',self.__shortcutf5)
        self.process_menu.addSeparator()
        self.whole_action=self.process_menu.addAction('结束整个进程树','F6',self.__shortcutf6)
        self.process_menu.addSeparator()
        self.current_action=self.process_menu.addAction('结束当前进程树','F7',self.__shortcutf7)
        self.process_menu.addSeparator()
        self.grab_action=self.process_menu.addAction('捕捉窗口','',self.__grab_action)
        CreateControl(QPushButton,self,10,10,50,30,'刷新',self.__refresh_processes)
        self.auto_refresh=CreateControl(QCheckBox,self,70,10,50,30,'自动')
        self.auto_refresh.setChecked(appconfig['process']['autorefresh'])
        self.auto_refresh.stateChanged.connect(self.__auto_refresh)
        self.pin_top=CreateControl(QCheckBox,self,120,10,50,30,'置顶')
        self.pin_top.setChecked(appconfig['process']['pintop'])
        self.pin_top.stateChanged.connect(self.__pin_top)
        self.search_process=CreateControl(QLineEdit,self,190,10,200,30,mainwindow.searchkeywords[2])
        self.search_process.setPlaceholderText('检索进程名和工具名')
        self.search_process.textChanged.connect(self.__search_process)
        self.process_tree=CreateControl(QTreeView,self,10,50,380,690)
        self.process_tree.setModel(self.model)
        self.process_tree.setStyleSheet('QTreeView::branch:closed:has-children{image:url(resources/icons/closed.png);}QTreeView::branch:open:has-children{image:url(resources/icons/opened.png);}')
        self.process_tree.contextMenuEvent=self.__process_tree_contextmenu
        self.process_tree.header().setDefaultAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.anchors=[[3,self.search_process],[8,self.process_tree]]
        self.timer=self.startTimer(1000) if appconfig['process']['autorefresh'] else 0
        self.__refreshtree()
        self.__refreshfilter()
    @AddWatcher
    def GetLevel(self,node:ProcessNode|None)->int:
        if node is None:return 0
        a=node.Layer()
        return max(a-2,0) if any(i.topic.ppid==node.root.pid for i in mainwindow.tab_area.SortedTabs()[1:]) else (a>2 or a==2 and node.parent.children.index(node))+1
    @AddWatcher
    def GetRoot(self,node:ProcessNode)->ProcessNode:
        return self.GetRoot(node.parent) if node.parent.parent and self.GetLevel(node.parent) else node
    @AddWatcher
    def GetSelectedNode(self)->ProcessNode|None:
        return self.process_tree.selectedIndexes()[0].internalPointer() if self.process_tree.selectedIndexes() else None
    @AddWatcher
    def __shortcutf5(self)->None:
        if (n:=self.__getfile(self.GetSelectedNode())):SelectFile(n)
    @AddWatcher
    def __shortcutf6(self)->None:
        if self.GetLevel(n:=self.GetSelectedNode()):self.__terminate(self.GetRoot(n).pid,True)
    @AddWatcher
    def __shortcutf7(self)->None:
        if self.GetLevel(n:=self.GetSelectedNode())>1:self.__terminate(n.pid,False)
    @AddWatcher
    def __grab_action(self)->None:
        n=self.GetRoot(self.GetSelectedNode())
        m=n.children[0].pid
        try:
            p=next(i for i in appconfig['residual'] if i[2]==m)
            t=n.name.removeprefix('[待捕捉] ')
            if mainwindow.tools.get(t,{}).get('type')!='cmd':RequestMessage('w',self,'警告','工具名称不一致，请检查是否修改过名称')
            elif win32process.GetWindowThreadProcessId(p[3])[1]==m:mainwindow.tab_area.AddTopic(EmbedCmdTopic(t,*p[1:]),mainwindow.icons['stopped'])
            else:
                appconfig['residual']=[i for i in appconfig['residual'] if i[2]!=m]
                mainwindow.SaveConfig()
                mainwindow.processlist=[i for i in mainwindow.processlist if i[1]!=p[1]]
                RequestMessage('w',self,'警告',f'窗口“{n.name}”捕捉失败。<br><span style="color:red">该进程窗口可能已被破坏，无法利用，已从进程列表移除。<br>请勿尝试结束进程，在较高版本 Windows 11 上会引发蓝屏重启！</span>')
        except:RequestMessage('w',self,'警告',f'没有找到窗口“{n.name}”，无法捕捉')
    @AddWatcher
    def __getfold(self,index:QModelIndex)->None:
        if index.isValid() and not self.process_tree.isExpanded(index):self.foldlist.append(index.internalPointer().pid)
        for i in range(self.model.rowCount(index)):self.__getfold(self.model.index(i,0,index))
    @AddWatcher
    def __refreshfilter(self)->None:
        self.model.filter=self.search_process.text().lower()
        self.process_tree.viewport().update()
    @AddWatcher
    def __refreshtree(self)->None:
        n=self.GetSelectedNode()
        self.selected=n.pid if n else 0
        self.foldlist.clear()
        self.__getfold(QModelIndex())
        self.process_tree.clearSelection()
        # p=[['',4]]
        # for i in psutil.process_iter(['pid','ppid']):
        #     try:
        #         if i.pid and not psutil.pid_exists(i.ppid()):p.append(['',i.pid])
        #     except:pass
        self.model.RefreshTree(mainwindow.processlist)
        self.process_tree.expandAll()
        self.__setfold(QModelIndex())
        self.process_tree.resizeColumnToContents(0)
        self.process_tree.resizeColumnToContents(1)
    @AddWatcher
    def __setfold(self,index:QModelIndex)->None:
        if self.selected and index.isValid() and index.internalPointer().pid==self.selected:
            self.process_tree.selectionModel().select(QItemSelection(index,index.sibling(index.row(),2)),QItemSelectionModel.SelectionFlag.Select)
            self.selected=0
        if index.isValid() and index.internalPointer().pid in self.foldlist:self.process_tree.setExpanded(index,False)
        for i in range(self.model.rowCount(index)):self.__setfold(self.model.index(i,0,index))
    @AddWatcher
    def __getfile(self,node:ProcessNode|None)->str:
        if node is None:return ''
        t=mainwindow.tools[node.root.name.removeprefix('[内嵌] ').removeprefix('[待捕捉] ')]
        if node.Layer()>2 or node.Layer()==2 and node.parent.children.index(node):
            c=[i.lower() for i in node.cmdline if i]
            match node.file.lower():
                case 'conhost.exe':return self.__getfile(node.parent)
                case 'java.exe':
                    for i,j in enumerate(c):
                        if j.lower() in ['-jar','--jar'] and i<len(c)-1:return PathSynthesis(apppath,t['path'],c[i+1])
                case 'python.exe':
                    for i in c:
                        if i in ['-c','-m']:return node.path
                        elif i[0]!='-' and (n:=GetExistsFileName(PathSynthesis(apppath,t['path'],i))):return n
            return node.path
        else:return f'{apppath}/{t['path']}/{t['file'].split(' ')[-1]}'
    @AddWatcher
    def __terminate(self,pid:int,whole:bool)->None:
        if RequestMessage('w',self,'警告',f'是否结束指定进程{'所在的整个进程树？' if whole else '及所有子进程？<br><span style="color:red">无特殊理由，推荐结束整个进程树，以避免各种潜在问题</span>'}',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            RequestMessage('w',self,'警告',f'进程树结束{'成功' if Terminate(pid) or not psutil.pid_exists(pid) else '失败'}')
            self.__refreshtree()
    @AddWatcher
    def __refresh_processes(self)->None:
        self.__refreshtree()
        self.process_tree.viewport().update()
    @AddWatcher
    def __auto_refresh(self,event:Qt.CheckState)->None:
        if self.auto_refresh.isChecked():self.timer=self.startTimer(1000)
        else:self.killTimer(self.timer)
        appconfig['process']['autorefresh']=self.auto_refresh.isChecked()
        mainwindow.SaveConfig()
    @AddWatcher
    def __pin_top(self,event:Qt.CheckState)->None:
        g=self.geometry()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,self.pin_top.isChecked())
        self.show()
        self.setGeometry(g)
        appconfig['process']['pintop']=self.pin_top.isChecked()
        mainwindow.SaveConfig()
    @AddWatcher
    def __search_process(self,text:str)->None:
        mainwindow.searchkeywords[2]=text
        self.__refreshfilter()
    @AddWatcher
    def __process_tree_contextmenu(self,event:QContextMenuEvent)->None:
        if self.process_tree.indexAt(event.pos()).isValid():
            p=self.GetSelectedNode()
            n=self.GetLevel(p)
            b=self.GetRoot(p).name.startswith('[待捕捉] ')
            self.whole_action.setVisible(not b and n)
            self.current_action.setVisible(not b and n>1)
            self.grab_action.setVisible(b)
            self.process_menu.exec(event.globalPos())
        else:self.process_tree.clearSelection()
    @AddWatcher
    def closeEvent(self,event:QCloseEvent)->None:
        mainwindow.processdialog=None
        return super().closeEvent(event)
    @AddWatcher
    def keyPressEvent(self,event:QKeyEvent)->None:
        if event.key()==Qt.Key.Key_Escape and not self.process_menu.isVisible():self.close()
        return super().keyPressEvent(event)
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        return super().resizeEvent(event)
    @AddWatcher
    def timerEvent(self,event:QTimerEvent)->None:
        self.__refreshtree()
        return super().timerEvent(event)

class ConfigDialog(QDialog):
    @AddWatcher
    def __init__(self)->None:
        super().__init__(mainwindow,Qt.WindowType.WindowCloseButtonHint)
        c=appconfig
        self.replaces=['','java8','java9+']
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose,True)
        self.setFixedSize(400,470)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle('系统配置')
        CreateControl(QLabel,self,10,10,80,25,'动画时长')
        self.anime_time=CreateControl(QDoubleSpinBox,self,100,10,290,25)
        self.anime_time.setDecimals(1)
        self.anime_time.setRange(0,2)
        self.anime_time.setSingleStep(0.5)
        self.anime_time.setValue(c['general']['animetime'])
        CreateControl(QLabel,self,10,45,80,25,'标签悬停')
        self.preview_value=RadioButtonGroup(self,100,45,290,25,['详细预览','简略预览','切换'],2-c['general']['preview'])
        self.preview_value.ReshapeItems([25,125,225],100)
        CreateControl(QLabel,self,10,80,80,25,'崩溃处理')
        self.grab_value=RadioButtonGroup(self,100,80,290,25,['释放','停止'],1-c['general']['grab'])
        CreateControl(QFrame,self,10,115,379,1).setStyleSheet('border:1px solid gray')
        CreateControl(QLabel,self,10,125,80,25,'历史记录')
        self.history_record=RadioButtonGroup(self,100,125,290,25,['开启','关闭'],1-c['history']['record'])
        CreateControl(QLabel,self,10,160,80,25,'显示数量')
        self.max_shown=CreateControl(QSpinBox,self,100,160,290,25)
        self.max_shown.setRange(9,99)
        self.max_shown.setValue(c['history']['maxshown'])
        CreateControl(QFrame,self,10,195,379,1).setStyleSheet('border:1px solid gray')
        CreateControl(QLabel,self,10,205,80,25,'自动刷新进程')
        self.process_autorefresh=RadioButtonGroup(self,100,205,290,25,['开启','关闭'],1-c['process']['autorefresh'])
        CreateControl(QLabel,self,10,240,80,25,'进程窗口置顶')
        self.process_pintop=RadioButtonGroup(self,100,240,290,25,['开启','关闭'],1-c['process']['pintop'])
        CreateControl(QFrame,self,10,275,379,1).setStyleSheet('border:1px solid gray')
        CreateControl(QLabel,self,10,285,80,25,'Java 重定向')
        self.java_replace=RadioButtonGroup(self,100,285,290,25,['不重定向','重定向为 Java 8','重定向为 Java 9+'],self.replaces.index(c['environment']['java']))
        self.java_replace.ReshapeItems([0,70,180],110)
        CreateControl(QLabel,self,10,320,80,25,'Java 8 路径')
        self.java8_value=CreateControl(QLineEdit,self,100,320,200,25,c['environment']['java8'])
        CreateControl(QPushButton,self,310,320,80,25,'选择',self.__buttons).target=self.java8_value
        CreateControl(QLabel,self,10,355,80,25,'Java 9+ 路径')
        self.java9plus_value=CreateControl(QLineEdit,self,100,355,200,25,c['environment']['java9+'])
        CreateControl(QPushButton,self,310,355,80,25,'选择',self.__buttons).target=self.java9plus_value
        CreateControl(QLabel,self,10,390,80,25,'Python 路径')
        self.python_value=CreateControl(QLineEdit,self,100,390,200,25,c['environment']['python'])
        CreateControl(QPushButton,self,310,390,80,25,'选择',self.__buttons).target=self.python_value
        for i in [self.grab_value,self.history_record,self.process_autorefresh,self.process_pintop]:i.ReshapeItems([60,170],110)
        self.ok_button=CreateControl(QPushButton,self,95,430,100,30,'确定',self.__ok_button)
        self.cancel_button=CreateControl(QPushButton,self,205,430,100,30,'取消',self.__cancel_button)
    @AddWatcher
    def __buttons(self)->None:
        m=self.sender().target
        if (n:=RequestFile('file',self,'选择运行环境文件',m.text() or apppath,f'运行环境 ({'python' if m is self.python_value else 'java'}.exe)')[0]):m.setText(n.removeprefix(f'{apppath}/'))
    @AddWatcher
    def __ok_button(self)->None:
        c=appconfig
        c['general']['animetime']=self.anime_time.value()
        c['general']['preview']=2-self.preview_value.GetValue()
        c['general']['grab']=not self.grab_value.GetValue()
        c['history']['record']=not self.history_record.GetValue()
        c['history']['maxshown']=self.max_shown.value()
        c['process']['autorefresh']=not self.process_autorefresh.GetValue()
        c['process']['pintop']=not self.process_pintop.GetValue()
        c['environment'].update({'java':self.replaces[self.java_replace.GetValue()],'java8':self.java8_value.text(),'java9+':self.java9plus_value.text(),'python':self.python_value.text()})
        mainwindow.SaveConfig()
        mainwindow.HomePage().RefreshHistory()
        self.done(-1)
    @AddWatcher
    def __cancel_button(self)->None:
        self.done(-1)

class EmbedCmdTopic(TopicBase):
    @AddWatcher
    def __init__(self,name:str,ppid:int=0,cpid:int=0,hwnd:int=0)->None:
        super().__init__(name)
        t=mainwindow.tools[name]
        self.config=t
        self.cpid=cpid
        self.executors=[]
        self.hwnd=hwnd
        self.model=QStandardItemModel()
        self.outputpath=f'{apppath}/{t['path']}/{t['output']}'.rstrip('/')
        self.ppid=ppid
        self.watcher=QFileSystemWatcher([self.outputpath])
        self.watcher.directoryChanged.connect(self.__watcherupdate)
        self.setAcceptDrops(True)
        self.mask_canvas=CreateControl(QFrame,self,0,0,1000,500)
        self.switch_help=CreateControl(QPushButton,self,10,10,85,30,'查看文档(&V)',self.__switch_help)
        self.command_text=CreateControl(QLineEdit,self,105,10,560,30,f'{GetPrefix(t['prefix'])} {t['file']}'.strip())
        self.command_text.keyReleaseEvent=self.__command_text
        self.command_button=CreateControl(QPushButton,self,675,10,85,30,'执行命令(&E)',self.__command_button)
        self.pause_resume=CreateControl(QPushButton,self,770,10,30,30,click=self.__pause_resume)
        self.report_folder=CreateControl(QPushButton,self,810,10,85,30,'配置输出(&F)',self.__report_folder)
        self.open_path=CreateControl(QPushButton,self,905,10,85,30,'打开目录(&D)',self.__open_path)
        self.command_area=CreateControl(QWidget,self,10,50,790,440)
        self.command_area.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.reboot_command=CreateControl(QPushButton,self.command_area,0,0,100,30,'重启命令行进程',self.__reboot_command)
        self.reboot_command.hide()
        self.help_browser=WebArea(self,30,70,750,290,f'{mainwindow.htmlhead}{ReadFile(f'resources/docs/{t['name']}.html') or '<h2>没有帮助文档</h2>'}<script>{mainwindow.htmlroot}{mainwindow.htmltail}</script>',self.__js_method_called,lambda:self.command_text.setFocus())
        self.help_browser.hide()
        self.output_list=CreateControl(QListView,self,810,50,180,440)
        self.output_list.setModel(self.model)
        self.output_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.output_list.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        self.output_list.doubleClicked.connect(self.__output_list_doubleclicked)
        self.output_list.contextMenuEvent=self.__output_list_contextmenu
        self.anchors=[[3,self.command_button,self.pause_resume,self.report_folder,self.open_path],[5,self.output_list],[6,self.command_text],[8,self.mask_canvas,self.command_area,self.help_browser]]
        self.__watcherupdate('')
        QTimer.singleShot(100,self.__createwindow)
    @AddWatcher
    def CleanUp(self,cleancode:int)->bool:
        if cleancode==1 and self.GetProcessList():return RequestMessage('w',mainwindow,'警告','请先结束正在执行的任务') and False
        else:
            CloseControl(self.help_browser)
            if self.hwnd:
                if cleancode==4 or cleancode==2 and self.GetProcessList():
                    win32gui.SetParent(self.hwnd,0)
                    win32gui.SetWindowLong(self.hwnd,win32con.GWL_STYLE,self.windowvalues[0])
                    win32gui.SetWindowLong(self.hwnd,win32con.GWL_EXSTYLE,self.windowvalues[1])
                    win32gui.ShowWindow(self.hwnd,win32con.SW_SHOWNORMAL)
                    win32gui.SetWindowPlacement(self.hwnd,self.windowvalues[2])
                else:
                    mainwindow.processlist=[i for i in mainwindow.processlist if i[1]!=self.ppid]
                    appconfig['residual']=[i for i in appconfig['residual'] if i[1]!=self.ppid]
                    Terminate(self.ppid)
                self.hwnd=0
            else:appconfig['residual']=[i for i in appconfig['residual'] if i[1]!=self.ppid]
            mainwindow.SaveConfig()
            return True
    @AddWatcher
    def GetProcessList(self)->list[psutil.Process]|None:
        try:return [i for i in psutil.Process(self.ppid).children(recursive=True) if i.name().lower() not in ['cmd.exe','powershell.exe'] and i.status() in [psutil.STATUS_RUNNING,psutil.STATUS_STOPPED]]
        except:
            self.hwnd=0
            return None
    @AddWatcher
    def GrabCommand(self)->list[str]:
        return [f'进程：{p[0].exe().split('\\')[-1]}',f'参数：{' '.join(p[0].cmdline()[1:])}'] if (p:=self.GetProcessList()) else ['进程：未运行','参数：无']
    @AddWatcher
    def GrabWindow(self)->QPixmap:
        if self.hwnd:
            r=win32gui.GetWindowRect(self.hwnd)
            w,h=r[2]-r[0],r[3]-r[1]
            d=win32gui.GetWindowDC(self.hwnd)
            p=win32ui.CreateDCFromHandle(d)
            q=p.CreateCompatibleDC()
            b=win32ui.CreateBitmap()
            b.CreateCompatibleBitmap(p,w,h)
            q.SelectObject(b)
            q.BitBlt((0,0),(w,h),p,(0,0),win32con.SRCCOPY)
            m=b.GetInfo()
            n=QImage(b.GetBitmapBits(True),m['bmWidth'],m['bmHeight'],QImage.Format.Format_RGB32)
            win32gui.DeleteObject(b.GetHandle())
            q.DeleteDC()
            p.DeleteDC()
            win32gui.ReleaseDC(self.hwnd,d)
            return QPixmap(n.copy())
        else:
            c=QPixmap(self.command_area.size())
            c.fill(Qt.GlobalColor.black)
            return c
    @AddWatcher
    def __createwindow(self)->None:
        if self.hwnd:self.__windowfounded(self.ppid,self.cpid,self.hwnd)
        else:
            self.founder=WindowFounder(self.config['path'])
            self.founder.signaler.connect(self.__windowfounded)
            self.founder.start()
    @AddWatcher
    def __windowfounded(self,ppid:int,cpid:int,hwnd:int)->None:
        self.windowvalues=[win32gui.GetWindowLong(hwnd,win32con.GWL_STYLE),win32gui.GetWindowLong(hwnd,win32con.GWL_EXSTYLE),win32gui.GetWindowPlacement(hwnd)]
        # win32gui.SetWindowLong(h,win32con.GWL_STYLE,win32gui.GetWindowLong(h,win32con.GWL_STYLE)&~0x00800000&~0x00010000)
        # win32gui.SetWindowLong(h,win32con.GWL_STYLE,win32gui.GetWindowLong(h,win32con.GWL_STYLE)&~(win32con.WS_CAPTION|win32con.WS_THICKFRAME)|win32con.WS_CHILD)
        win32gui.SetWindowLong(hwnd,win32con.GWL_STYLE,0x10000000)
        win32gui.SetParent(hwnd,self.command_area.winId())
        win32gui.ShowWindow(hwnd,1)
        if self.hwnd:
            for i in mainwindow.processlist:
                if i[1]==ppid:i[0]=i[0].replace('[待捕捉] ','[内嵌] ')
        else:mainwindow.AppendUsing(f'[内嵌] {self.title}',ppid,cpid,hwnd)
        self.cpid=cpid
        self.hwnd=hwnd
        self.ppid=ppid
        self.reboot_command.show()
        self.__resizewindow()
        self.resize(self.size()-QSize(0,1))
        self.resize(self.size()+QSize(0,1))
    @AddWatcher
    def __watcherupdate(self,path:str)->None:
        self.model.clear()
        for i in sorted((i for j in (self.config['format'] or '*.txt').split(',') for i in pathlib.Path(self.outputpath).glob(j)),key=lambda i:i.name):self.model.appendRow(QStandardItem(GetFileIcon(i),i.name))
    @AddWatcher
    def __resizewindow(self)->None:
        r=QGuiApplication.primaryScreen().devicePixelRatio()
        self.reboot_command.move(self.command_area.width()//2-50,self.command_area.height()//2-15)
        if self.hwnd:win32gui.MoveWindow(self.hwnd,0,0,int(self.command_area.width()*r),int(self.command_area.height()*r),True)
    @AddWatcher
    def __switch_help(self)->None:
        if self.help_browser.isVisible():
            self.help_browser.hide()
            self.command_text.setFocus()
        else:self.help_browser.show()
    @AddWatcher
    def __command_text(self,event:QKeyEvent)->None:
        if event.key()==Qt.Key.Key_Escape and self.help_browser.isVisible():self.help_browser.hide()
        elif event.key() in [Qt.Key.Key_Enter,Qt.Key.Key_Return]:self.__command_button()
    @AddWatcher
    def __command_button(self)->None:
        if self.hwnd and self.command_text.text():
            for i in f'{self.command_text.text()}\r':
                win32gui.PostMessage(self.hwnd,win32con.WM_CHAR,ord(i),0)
                time.sleep(0.01)
    @AddWatcher
    def __pause_resume(self)->None:
        if (p:=self.GetProcessList()):
            match p[0].status():
                case psutil.STATUS_RUNNING:
                    p[0].suspend()
                    self.pause_resume.setIcon(mainwindow.icons['play'])
                case psutil.STATUS_STOPPED:
                    p[0].resume()
                    self.pause_resume.setIcon(mainwindow.icons['pause'])
    @AddWatcher
    def __report_folder(self)->None:
        p=f'{apppath}/{self.config['path']}/'
        if (n:=RequestFile('files',self,'选择结果文件，支持同时选择最多5种不同格式的文件',f'{self.config['path']}/{self.config['output']}')[0]):
            if ':' in n[0].removeprefix(p):return RequestMessage('w',self,'警告','不能将工具目录外部的文件设置为结果文件')
            if RequestMessage('q',self,'提示','该操作不会修改工具本身保存结果的路径，只修改工具箱监控目录，是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                m=GetOutputFormat(p,n)
                self.config['output']=m[0]
                self.outputpath=f'{apppath}/{self.config['path']}/{self.config['output']}'.rstrip('/')
                self.config['format']=m[1]
                self.watcher.removePaths(self.watcher.directories())
                self.watcher.addPath(self.outputpath)
                self.__watcherupdate('')
                mainwindow.SaveTools(2,self.config|{'oldname':self.config['name']})
    @AddWatcher
    def __open_path(self)->None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(QDir.toNativeSeparators(f'{apppath}/{self.config['path']}/{self.config['output']}')))
    @AddWatcher
    def __reboot_command(self)->None:
        self.__createwindow()
        self.reboot_command.hide()
    @AddWatcher
    def __output_list_contextmenu(self,event:QContextMenuEvent)->None:
        b=len(self.output_list.selectedIndexes())
        m=QApplication.clipboard().mimeData()
        n=[i for i in [GetExistsFileName(i.toLocalFile()) for i in m.urls()] if i]
        t='剪切' if m.hasFormat('application/x-qt-windows-mime;value="Preferred DropEffect"') and m.data('application/x-qt-windows-mime;value="Preferred DropEffect"')==b'\x02\x00\x00\x00' else '复制'
        mainwindow.copy_action.setEnabled(b)
        mainwindow.cut_action.setEnabled(b)
        mainwindow.paste_action.setEnabled(bool(n))
        mainwindow.paste_action.setText(f'{t}粘贴' if n else '粘贴')
        mainwindow.paste_action.setToolTip(f'正在{t}文件：\n{'\n'.join(n)}' if n else '')
        mainwindow.delete_action.setEnabled(b)
        mainwindow.copypath_action.setEnabled(b==1)
        mainwindow.rename_action.setEnabled(b==1)
        mainwindow.send_action.setEnabled(b==1)
        mainwindow.output_menu.exec(event.globalPos())
    @AddWatcher
    def __output_list_doubleclicked(self,index:QModelIndex)->None:
        QDesktopServices.openUrl(QUrl(f'file:///{self.outputpath}/{self.model.data(index)}'))
    @AddWatcher
    def __js_method_called(self,argument:list)->None:
        t=self.command_text
        r=t.text().strip()
        s=' '*bool(r and r[-1]!='=')
        match argument[0]:
            case '':
                n=argument[1].split(',')[0].split(' ')[0]
                t.setText(f'{r}{s}{f'{n.split('=')[0]}=' if '=' in n else f'{n} '}')
            case 'full':t.setText(f'{r}{s}{argument[1]} ')
            case 'usage':
                a=argument[1].split(' [')[0].split(' ')
                a[0]=GetPrefix(self.config['prefix']).removesuffix(' -jar') or a[0]
                t.setText(f'{' '.join(a)} ')
        t.setFocus()
    @AddWatcher
    def resizeEvent(self,event:QResizeEvent)->None:
        Reshape(self,event)
        self.__resizewindow()
        return super().resizeEvent(event)

QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
app=QApplication(sys.argv)
app.setFont(QFont('SimHei',9))
app.setStartDragDistance(100)
app.setStyle('Fusion')
app.setStyleSheet('QDialog{font-family:"SimHei";}')
appconfig={}
appiconprovider=QFileIconProvider()
apppath=str(pathlib.Path.cwd()).replace('\\','/')
appuser=psutil.Process(os.getpid()).username()
mainwindow=MainWindow()
app.installEventFilter(mainwindow)

if __name__=='__main__':
    mainwindow.show()
    sys.exit(app.exec())
