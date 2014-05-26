# LeCrunch
# Copyright (C) 2010 Anthony LaTorre 
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import re
import array
import StringIO
import struct
import numpy as np
import sock

# data types in lecroy binary blocks, where:
# length  -- byte length of type
# string  -- string representation of type
# packfmt -- format string for struct.unpack()
class String:
    length = 16
    string = 'string'
class Byte:
    length = 1
    string = 'byte'
    packfmt = 'b'
class Word:
    length = 2
    string = 'word'
    packfmt = 'h'
class Long:
    length = 4
    string = 'long'
    packfmt = 'l'
class Enum:
    length = 2
    string = 'enum'
    packfmt = 'h'
class Float:
    length = 4
    string = 'float'
    packfmt = 'f'
class Double:
    length = 8
    string = 'double'
    packfmt = 'd'
class TimeStamp:
    length = 16
    string = 'time_stamp'
    packfmt = 'dbbbbhh'
class UnitDefinition:
    length = 48
    string = 'unit_definition'

# byte length of wavedesc block
wavedesclength = 346

# template of wavedesc block, where each entry in tuple is:
# (variable name, byte position from beginning of block, datatype)
wavedesc_template = ( ('descriptor_name'    , 0   , String),
                      ('template_name'      , 16  , String),
                      ('comm_type'          , 32  , Enum),
                      ('comm_order'         , 34  , Enum),
                      ('wave_descriptor'    , 36  , Long),
                      ('user_text'          , 40  , Long),
                      ('res_desc1'          , 44  , Long),
                      ('trigtime_array'     , 48  , Long),
                      ('ris_time_array'     , 52  , Long),
                      ('res_array1'         , 56  , Long),
                      ('wave_array_1'       , 60  , Long),
                      ('wave_array_2'       , 64  , Long),
                      ('res_array_2'        , 68  , Long),
                      ('res_array_3'        , 72  , Long),
                      ('instrument_name'    , 76  , String),
                      ('instrument_number'  , 92  , Long),
                      ('trace_label'        , 96  , String),
                      ('reserved1'          , 112 , Word),
                      ('reserved2'          , 114 , Word),
                      ('wave_array_count'   , 116 , Long),
                      ('pnts_per_screen'    , 120 , Long),
                      ('first_valid_pnt'    , 124 , Long),
                      ('last_valid_pnt'     , 128 , Long),
                      ('first_point'        , 132 , Long),
                      ('sparsing_factor'    , 136 , Long),
                      ('segment_index'      , 140 , Long),
                      ('subarray_count'     , 144 , Long),
                      ('sweeps_per_acq'     , 148 , Long),
                      ('points_per_pair'    , 152 , Word),
                      ('pair_offset'        , 154 , Word),
                      ('vertical_gain'      , 156 , Float),
                      ('vertical_offset'    , 160 , Float),
                      ('max_value'          , 164 , Float),
                      ('min_value'          , 168 , Float),
                      ('nominal_bits'       , 172 , Word),
                      ('nom_subarray_count' , 174 , Word),
                      ('horiz_interval'     , 176 , Float),
                      ('horiz_offset'       , 180 , Double),
                      ('pixel_offset'       , 188 , Double),
                      ('vertunit'           , 196 , UnitDefinition),
                      ('horunit'            , 244 , UnitDefinition),
                      ('horiz_uncertainty'  , 292 , Float),
                      ('trigger_time'       , 296 , TimeStamp),
                      ('acq_duration'       , 312 , Float),
                      ('record_type'        , 316 , Enum),
                      ('processing_done'    , 318 , Enum),
                      ('reserved5'          , 320 , Word),
                      ('ris_sweeps'         , 322 , Word),
                      ('timebase'           , 324 , Enum),
                      ('vert_coupling'      , 326 , Enum),
                      ('probe_att'          , 328 , Float),
                      ('fixed_vert_gain'    , 332 , Enum),
                      ('bandwidth_limit'    , 334 , Enum),
                      ('vertical_vernier'   , 336 , Float),
                      ('acq_vert_offset'    , 340 , Float),
                      ('wave_source'        , 344 , Enum) )

class LeCroyScope(sock.Socket):
    """
    A class for triggering and fetching waveforms from the oscilloscope.
    """
    def __init__(self, *args, **kwargs):
        super(LeCroyScope, self).__init__(*args, **kwargs)
        self.send('comm_header short')
        self.check_last_command()
        self.send('comm_format DEF9,BYTE,BIN')
        self.check_last_command()

    def getchannels(self):
        """Returns a list of the active channels on the scope."""
        channels = []
        for i in range(1, 5):
            self.send('c%i:trace?' %i)
            if 'ON' in self.recv():
                channels.append(i)
        return channels

    def trigger(self):
        """Trigger the oscilloscope and wait for an acquisition."""
        self.send('arm;wait')

    def getwavedesc(self, channel):
        if channel not in range(1, 5):
            raise Exception('channel must be in %s.' % str(range(1, 5)))

        self.send('c%s:wf? desc' % str(channel))

        msg = self.recv()
        if not int(msg[1]) == channel:
            raise RuntimeError('waveforms out of sync or comm_header is off.')

        data = StringIO.StringIO(msg)

        startpos = re.search('WAVEDESC', data.read()).start()

        wavedesc = {}

        # check endian
        data.seek(startpos + 34)
        if struct.unpack('<'+Enum.packfmt, data.read(Enum.length)) == 0:
            endian = '>'
            wavedesc['little_endian'] = True
            np.little_endian = True
        else:
            endian = '<'
            wavedesc['little_endian'] = False
            np.little_endian = False

        data.seek(startpos)

        # build dictionary of wave description
        for name, pos, datatype in wavedesc_template:
            raw = data.read(datatype.length)
            if datatype in (String, UnitDefinition):
                wavedesc[name] = raw.rstrip('\x00')
            elif datatype in (TimeStamp,):
                wavedesc[name] = struct.unpack(endian+datatype.packfmt, raw)
            else:
                wavedesc[name] = struct.unpack(endian+datatype.packfmt, raw)[0]

        # determine data type
        if wavedesc['comm_type'] == 0:
            wavedesc['dtype'] = np.int8
        elif wavedesc['comm_type'] == 1:
            wavedesc['dtype'] = np.int16
        else:
            raise Exception('unknown comm_type.')
            
        return wavedesc

    def getwaveform(self, channel, wavedesc):
        """
        Request, process, and return the voltage array for channel number
        `channel` from the oscilloscope as a numpy array.
        """ 

        if channel not in range(1, 5):
            raise Exception('channel must be in %s.' % str(range(1, 5)))

        self.send('c%s:wf? dat1' % str(channel))

        msg = self.recv()
        if not int(msg[1]) == channel:
            raise RuntimeError('waveforms out of sync or comm_header is off.')

        return np.fromstring(msg[22:], wavedesc['dtype'], wavedesc['wave_array_count'])


class WaveDescription(object):
    def __init__(self, desc):
        self.__dict__.update(desc)

    def __getitem__(self, item):
        return self.__dict__[item]

    def __str__(self):
        return "WaveDescription(label=%s, counts=%i)" % (self.trace_label, self.wave_array_count)

    def __repr__(self):
        return self.__dict__.__repr__()


if __name__ == '__main__':
    import argparse
    from matplotlib import pyplot as plt

    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", type=str,
                        help="IP Address of LeCroy device",
                        default='131.246.148.86')

    args = parser.parse_args()

    lc = LeCroyScope(args.ip)
    channels = lc.getchannels()
    fig, axes = plt.subplots(len(channels))
    if len(channels) == 1:
        axes = [axes]
    for c in channels:
        wave_desc = WaveDescription(lc.getwavedesc(c))
        wave = lc.getwaveform(c, wave_desc)
        print(wave_desc)
        axes[c - 1].plot(wave, '-r')
    plt.show()