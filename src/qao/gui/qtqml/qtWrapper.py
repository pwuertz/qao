'''
Created on 14.03.2014

@author: lausch
'''


def _qt_ucc(name):
    return name[0].upper() + name[1:]


def _qt_get(name):
    return ['    def get%s(self):' % _qt_ucc(name),
            '        return self._%s' % name]


def _qt_set(name, set_=None, notify=None):
    if set_ == None:
        set_ = "set%s" % _qt_ucc(name)
    if not notify:
        notify = '%sChanged' % name
    return ['    def %s(self, value):' % set_,
            '        if value != self._%s:' % name,
            '            self._%s = value' % name,
            '            self.%s.emit(value)' % notify]


def _qt_wrap_set(name, wrapped, set_=None, notify=None):
    if set_ == None:
        set_ = "set%s" % _qt_ucc(name)
    if not notify:
        notify = '%sChanged' % name
    if '(' not in wrapped:
        wrapped += '('
    return ['    def %s(self, value):' % set_,
            '        if value != self._%s:' % name,
            '            self._%s = value' % name,
            '            %svalue)' % wrapped,
            '            self.%s.emit(value)' % notify]


def _qt_notify(notify, dtype):
    if dtype == None:
        dtype = ''
    return '    %s = QtCore.pyqtSignal(%s)' % (notify, dtype)


def _qt_prop(name, dtype, get, set_, notify):
    if set_ == None or set_ == '':
        return '    %s = QtCore.pyqtProperty(%s, %s, notify=%s)' % (
                name, dtype, get, notify)
    if set_.startswith('self.'):
        set_ = set_[4:]
    return '    %s = QtCore.pyqtProperty(%s, %s, %s, notify=%s)' % (
                name, dtype, get, set_, notify)


class qt_wrapped(object):
    def __init__(self, class_description, author=None, version=None, doc=None):

        self.author = author
        self.version = version
        self.doc = doc
        self.class_description = class_description

    def _qt_create(self, name, dtype, get=None, set_=None, notify=None):
        if not isinstance(dtype, str):
            dtype = dtype.__name__
        if notify == None:
            notify = '%sChanged' % name
            self.notifications.append(_qt_notify(notify, dtype))
            if set_ != None and len(set_) > 0 and set_ != "set%s" % _qt_ucc(name):
                wrapped, set_ = (set_, "set%s" % _qt_ucc(name))
                self.f_defs[set_] = _qt_wrap_set(name, wrapped, set_, notify)
        if get == None:
            get = 'get%s' % _qt_ucc(name)
            self.f_defs[get] = _qt_get(name)
        if set_ == None:
            set_ = 'set%s' % _qt_ucc(name)
            self.f_defs[set_] = _qt_set(name, set_)
        self.props.append(_qt_prop(name, dtype, get, set_, notify))

    def _parse_props(self):
        self.props = []
        self.f_defs = {}
        self.notifications = []

        for f_name, f_item in self.class_description.items():
            if len(f_item) == 2:
                if f_item[1] == 'gsn':
                    self._qt_create(f_name, f_item[0])
                elif f_item[1] == 'gn':
                    self._qt_create(f_name, f_item[0], set_='')
                else:
                    self._qt_create(f_name, f_item[0], f_item[1])
            else:
                self._qt_create(f_name, *f_item)

        self.notifications = sorted(self.notifications, key=lambda p: (len(p), p))
        self.props = sorted(self.props, key=lambda p: (len(p), p))

    def get_code(self):
        self._parse_props()
        code = []
        code += ['\n    # signals',
                 '\n'.join(self.notifications),
                 '\n    # functions',
                 '\n\n'.join(['\n'.join(self.f_defs[f_name]) for f_name in sorted(self.f_defs.keys())]),
                 '\n    # props',
                 '\n'.join(self.props)]

        return code

    def __str__(self):
        return '\n'.join(self.get_code())

if __name__ == '__main__':
    #TODO: write example code
    pass
