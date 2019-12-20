#!/usr/bin/env python3
import re
import os
from modes import InputModes
import instruments
from operator import truediv, itemgetter
import math


class SongParser:

    def __init__(self):

        self.input_mode = None
        self.note_parser = None
        self.icon_delimiter = ' '
        self.pause = '.'
        self.quaver_delimiter = '-'
        self.comment_delimiter = '#'
        self.repeat_indicator = '*'


    def set_delimiters(self, icon_delimiter=' ', pause='.', quaver_delimiter='-', comment_delimiter='#', repeat_indicator='*'):

        self.icon_delimiter = icon_delimiter
        self.pause = pause
        self.quaver_delimiter = quaver_delimiter
        self.comment_delimiter = comment_delimiter
        self.repeat_indicator = repeat_indicator


    def check_delimiters(self):

        if self.input_mode == InputModes.JIANPU or isinstance(self.note_parser, JianpuNoteParser):
            if self.pause != '0':
                print('Jianpu notation is used: setting 0 as the pause character instead of '+self.pause)
                self.pause = '0'
            if self.quaver_delimiter == '-':
                print('Jianpu notation is used: setting ^ as the quaver delimiter instead of '+self.quaver_delimiter)
                self.quaver_delimiter = '^'

        delims = [self.icon_delimiter, self.pause, self.quaver_delimiter, self.comment_delimiter, self.repeat_indicator]

        parser = self.get_note_parser()
        if parser != None:
            for delim in delims:
                if (parser.not_note_name_regex.match(delim) == None or parser.not_octave_regex.match(delim) == None) and delim != self.comment_delimiter:
                    print('You chose an invalid delimiter for notation '+self.input_mode.value[1]+': '+delim)
                if delims.count(delim)>1:
                    print('You chose twice the same delimiter for notation '+self.input_mode.value[1]+': '+delim)


    def get_possible_modes(self, song_lines=None):

        if self.input_mode != None:
            return [self.input_mode]
        else:
            return self.detect_input_mode(song_lines)


    def set_input_mode(self, input_mode):

        if isinstance(input_mode, InputModes):
            self.input_mode = input_mode
            self.set_note_parser(self.input_mode)
            self.check_delimiters()


    def get_note_parser(self, input_mode=None):

        if self.note_parser != None:
            return self.note_parser

        if input_mode == None:
            input_mode = self.input_mode

        note_parser = None

        if input_mode == InputModes.SKYKEYBOARD:
            note_parser = SkyKeyboardNoteParser()
        elif input_mode == InputModes.SKY:
            note_parser = SkyNoteParser()
        elif input_mode == InputModes.ENGLISH:
            note_parser = EnglishNoteParser()
        elif input_mode == InputModes.DOREMI:
            note_parser = DoremiNoteParser()
        elif input_mode == InputModes.JIANPU:
            note_parser = JianpuNoteParser()
        elif input_mode == InputModes.ENGLISHCHORDS:
            note_parser = EnglishChordsNoteParser()

        return note_parser


    def set_note_parser(self, input_mode=None):

        if input_mode == None:
            input_mode = self.input_mode
        self.note_parser = self.get_note_parser(input_mode)


    def get_keyboard_layout(self):

        return SkyKeyboardNoteParser().keyboard_layout

    def split_icon(self, icon, delimiter=None):

        '''
        An icon is a collection of chords assembled with '-': ['A1C2-F3D4', 'C#4B4-Gb3A2']
        This method splits an icon into alist of chords:  ['A1C2', 'F3D4', 'C#4B4', 'Gb3A2']
        '''

        if delimiter == None:
            delimiter = self.quaver_delimiter
        return icon.split(delimiter)


    def split_chord(self, chord, note_parser=None):
        '''
        A chord is a collection of notes glued together:  ['A1C2', 'F3D4', 'C#4B4', 'Gb3A2']
        This method splits each chord into a list of notes: [['A1',C2'], ['F3','D4'],...]
        '''
        try:
            repeat = int(re.split(re.escape(self.repeat_indicator), chord)[1])
            chord = re.split(re.escape(self.repeat_indicator), chord)[0]
        except:
            repeat = 1

        if note_parser == None:
            note_parser = self.note_parser

        try:
            chord = note_parser.note_name_regex.sub(' \\1', chord).split()
        except AttributeError as err:
            print(err)

        return repeat, chord



    def parse_chords(self, chords, song_key='C', note_shift=0):
        #Individual note is a single-element list: chords=['A5']
        #Real chord is a single element list: chords=['B1A1A3']
        #Triplets and quavers are a list of notes or chords: chords=['B2', 'B3B1', 'B4', 'B5', 'C1', 'C2']
        harp_broken = True
        chord_skygrid = {}

        try:
            repeat = int(re.split(re.escape(repeat_indicator), chord)[1])
            chord = re.split(re.escape(repeat_indicator), chord)[0]
        except:
            repeat = 1

        #print(chord)
        if len(chords)>1:
            idx0 = 1 #Notes in quavers and triplets have a frame index >1
        else:
            idx0 = 0 #Single note or note in chord has a frame index ==0

        if self.note_parser == None:
           self.set_note_parser()

        for chord_idx, chord in enumerate(chords):
            '''
            Creates a skygrid from the harp's chord notes
            # For each chord, sets the highlighted state of each note accordingly (True or False)
            '''
            #TODO: this line is useless since we don't use position maps anymore.
            #chord = re.sub(re.escape(self.pause), '.', chord) #Replaces the pause character by the default

            if isinstance(self.note_parser, EnglishChordsNoteParser):
                chord = self.note_parser.decode_chord(chord)

            repeat, chord = self.split_chord(chord)
            #Now the real chord has been split in notes (1 note = 1 list slot)

            harp_broken = False
            harp_silent = False
            for note in chord: # Chord is a list of notes
                #Except InvalidLetterException
                try:
                    if note == self.pause:
                        highlighted_note_position = (-1, -1)
                    else:
                        highlighted_note_position = self.note_parser.calculate_coordinate_for_note(note, song_key, note_shift)
                except (KeyError, SyntaxError) as err:
                    print(err)
                    harp_broken = True
                else:
                    chord_skygrid[highlighted_note_position] = {}
                    chord_skygrid[highlighted_note_position][idx0+chord_idx] = True
                    harp_silent = False
                    if highlighted_note_position[0] < 0 and highlighted_note_position[1] < 0: #Note is a silence
                        chord_skygrid[highlighted_note_position][idx0+chord_idx] = False
                        harp_silent = True

        results = [chord_skygrid, harp_broken, harp_silent, repeat]
        return results


    def parse_line(self, line, song_key='C', note_shift=0):
        '''
        Returns instrument_line: a list of chord 'skygrid' (1 chord = 1 dict)
        '''
        instrument_line = []
        line = line.strip()
        line = re.sub(re.escape(self.icon_delimiter)+'{2,'+str(max(2,len(line)))+'}',self.icon_delimiter,line)#removes surnumerous spaces
        if len(line)>0:
            if line[0] == self.comment_delimiter:
                lyrics = line.split(self.comment_delimiter)
                for lyric in lyrics:
                    if len(lyric)>0:
                        voice = instruments.Voice()
                        voice.set_lyric(lyric.strip())
                        instrument_line.append(voice)
            else:
                icons=line.split(self.icon_delimiter)
                for icon in icons:
                    chords = self.split_icon(icon)
                    #From here, real chords are still glued, quavers have been split in different list slots
                    chord_skygrid, harp_broken, harp_silent, repeat = self.parse_chords(chords, song_key, note_shift)
                    harp = instruments.Harp()
                    harp.set_repeat(repeat)
                    harp.set_is_silent(harp_silent)
                    harp.set_is_broken(harp_broken)
                    harp.set_chord_skygrid(chord_skygrid)

                    instrument_line.append(harp)

        return instrument_line


    def find_key(self, song_lines):

       if self.note_parser == None:
           self.set_note_parser()
       #print('note parser is:')
       #print(self.note_parser)

       try:
           possible_keys = [k for k in self.note_parser.CHROMATIC_SCALE_DICT.keys()]
           isNoteRegEx = self.note_parser.note_name_regex
           notNoteRegEx = self.note_parser.not_note_name_regex
           #print(possible_keys)
       except AttributeError:
            #Parsers not having a chromatic scale keys should return None, eg Sky and Skykeyboard
           return None
       #print(possible_keys)
       scores = [0]*len(possible_keys)
       num_notes = [0]*len(possible_keys)
       for line in song_lines:
          if len(line)>0:
             if line[0] != self.comment_delimiter:

                notes = isNoteRegEx.sub(' \\1',notNoteRegEx.sub('',line)).split() # Clean-up, adds space and split
                #print(notes)
                for i,k in enumerate(possible_keys):
                   for note in notes:
                      num_notes[i] += 1
                      try:
                          #TODO: Support for Jianpu which uses a different octave indexing system
                            self.note_parser.calculate_coordinate_for_note(note, k, note_shift=0)
                      except KeyError:
                         scores[i]+=1
                      except SyntaxError:#Wrongly formatted notes are ignored
                         num_notes[i] -= 1

       #print(scores)
       num_notes = [1 if x == 0 else x for x in num_notes]
       #Removes zeros to avoid division by zero
       scores = list(map(truediv, scores, num_notes))
       scores = [(1 - score) for score in scores]

       #duplicates_dict = self.CHROMATIC_SCALE_DICT
       return self.most_likely(scores, possible_keys, 0.9, self.note_parser.CHROMATIC_SCALE_DICT)

       #print(scores)
#       sorted_idx, sorted_scores = zip(*sorted([(i,e) for i,e in enumerate(scores)], key=itemgetter(1), reverse=True))
#       sorted_keys = [possible_keys[i] for i in sorted_idx]
#       #print(sorted_scores)
#       #print(sorted_keys)
#
#       if sorted_scores[0] == 1:
#          if (sorted_scores[1] < 1) or (sorted_scores[2] < 1 and self.CHROMATIC_SCALE_DICT[sorted_keys[0]]==self.CHROMATIC_SCALE_DICT[sorted_keys[1]]):
#                 print('A unique key was found.')
#                 return [sorted_keys[0]]
#          else:
#              print('Several matching keys were found.')
#              return [k for i,k in enumerate(sorted_keys) if sorted_scores[i]==1 ]
#       elif (sorted_scores[0] > 0.95):
#           sorted_scores = list(map(truediv, sorted_scores, [max(sorted_scores)]*len(sorted_scores)))
#       sorted_keys = [k for i,k in enumerate(sorted_keys) if sorted_scores[i]>0.9]
#       if len(sorted_keys)==0:
#           #print('No matching key found.')
#           return []
#       else:
#           #print('One or several best matching keys were found.')
#           return sorted_keys


    def detect_input_mode(self, song_lines):
        '''
        Attempts to detect input musical notation
        '''
        possible_modes = [mode for mode in InputModes]
        possible_parsers = [self.get_note_parser(mode) for mode in possible_modes]
        #position_maps = [self.get_note_parser(mode).position_map for mode in possible_modes]
        possible_regex = [parser.single_note_name_regex for parser in possible_parsers]

        good_notes = [0]*len(possible_modes)
        num_notes = [0]*len(possible_modes)
        DEFG_notes = 0
        octave_span = 0

        for line in song_lines:
            line = line.strip()
            line = re.sub(re.escape(self.icon_delimiter)+'{2,'+str(max(2,len(line)))+'}',self.icon_delimiter,line)#removes surnumerous spaces
            if len(line) > 0:
                if line[0] != self.comment_delimiter:
                    icons=line.split(self.icon_delimiter)
                    for icon in icons:
                        chords = self.split_icon(icon)
                        for chord in chords:
                            for idx, possible_mode in enumerate(possible_modes):

                                if possible_mode == InputModes.ENGLISHCHORDS:
                                    notes = [chord] #Because abbreviated chord names are not composed of note names
                                    good_notes[idx] += sum([int(note in possible_parsers[idx].english_chords.keys()) for note in notes])
                                else:
                                    repeat, notes = self.split_chord(chord, possible_parsers[idx])
                                    good_notes[idx] += sum([int(possible_regex[idx].match(note) != None) for note in notes if note != self.pause])
                                #TODO: use self.map_note_to_position?

                                num_notes[idx] += sum([1 for note in notes if note != self.pause])

                                if possible_mode == InputModes.ENGLISH:
                                    DEFG_notes += sum([int(re.search('[D-G]',note) != None) for note in notes])
                                    octaves = [re.search('\d',note) for note in notes]

                                    octaves = sorted([int(octave.group(0)) for octave in octaves if octave != None])
                                    if len(octaves)>0:
                                        octave_span = max(octave_span, octaves[-1] - octaves[0] + 1)

        num_notes = [1 if x == 0 else x for x in num_notes] #Removes zeros to avoid division by zero

        scores = list(map(truediv, good_notes, num_notes))
        DEFG_notes /= num_notes[possible_modes.index(InputModes.ENGLISH)]

        if ((DEFG_notes == 0) or (DEFG_notes < 0.01 and octave_span > 2)) and (num_notes[possible_modes.index(InputModes.ENGLISH)] > 10):
            scores[possible_modes.index(InputModes.ENGLISH)] *= 0.5
        #print(scores)

        return self.most_likely(scores, possible_modes, 0.9)

#        sorted_inds, sorted_scores = zip(*sorted([(i,e) for i,e in enumerate(scores)], key=itemgetter(1), reverse=True))
#        if sorted_scores[0] == 1 and sorted_scores[1] < 1:
#            self.input_mode = possible_modes[sorted_inds[0]]
#            return [self.input_mode]
#        elif (sorted_scores[0] > 0.9):
#            sorted_scores = list(map(truediv, sorted_scores, [max(sorted_scores)]*len(sorted_scores)))
#            if sorted_scores[1] < 0.9:
#                return [possible_modes[sorted_inds[0]]]
#            else:
#                return possible_modes
#        else:
#            return possible_modes


    def most_likely(self,scores, items, threshold=0.9, duplicates_dict=None):

        if len(scores) == 0:
            return None
        if len(scores) == 1:
            return [items[0]]

        sorted_idx, sorted_scores = zip(*sorted([(i,e) for i,e in enumerate(scores)], key=itemgetter(1), reverse=True))

        sorted_items = [items[i] for i in sorted_idx]
       #print(sorted_scores)
       #print(sorted_items)

        if sorted_scores[0] == 1 and sorted_scores[1] < 1:
            return [sorted_items[0]]

        if sorted_scores[0] == 1 and sorted_scores[1] == 1:
            if duplicates_dict != None:
                try:
                    if sorted_scores[2] < 1 and duplicates_dict[sorted_items[0]] == duplicates_dict[sorted_items[1]]:
                        return [sorted_items[0]]
                except (IndexError,KeyError):
                    pass
            return [k for i,k in enumerate(sorted_items) if sorted_scores[i]==1]

        if (sorted_scores[0] < threshold):
            contrasts = [(score-min(sorted_scores))/(score+min(sorted_scores)) if score!=0 else 0 for score in sorted_scores ]
            sorted_items = [k for i,k in enumerate(sorted_items) if sorted_scores[i]>threshold/2]
        else:
            sorted_scores = list(map(truediv, sorted_scores, [max(sorted_scores)]*len(sorted_scores)))
            over_items = [k for i,k in enumerate(sorted_items) if sorted_scores[i]>threshold]
            if len(over_items)!=0:
               sorted_items = over_items

        if duplicates_dict != None:
            #Remove synonyms
            for i in range(1,len(sorted_items),2):
                if duplicates_dict[sorted_items[i]] == duplicates_dict[sorted_items[i-1]]:
                    sorted_items[i] = None
            sorted_items = [item for item in sorted_items if item != None]

        if len(sorted_items) == 0:
            return items
        else:
            return sorted_items


class NoteParser:

    '''
    A generic NoteParser for parsing notes of a major scale, and turning them into the corresponding coordinate on Sky's 3*5 piano.
    '''

    def __init__(self):

        self.columns = 5
        self.rows = 3

        self.CHROMATIC_SCALE_DICT = {}
        self.SEMITONE_INTERVAL_TO_MAJOR_SCALE_INTERVAL_DICT = {
            0: 0, # 0 semitones means it’s the root note
            2: 1, # 2 semitones means it’s a 2nd interval
            4: 2, # 4 semitones means it’s a 3rd interval
            5: 3, # 5 semitones means it’s a 4th interval
            7: 4, # 7 semitones means it’s a 5th interval
            9: 5, # 9 semitones means it’s a 6th interval
            11: 6 # 11 semitones means it’s a 7th interval
            }

        # Number of notes in the chromatic scale, and number of notes in a major scale
        self.CHROMATIC_SCALE_COUNT = 12
        self.BASE_OF_MAJOR_SCALE = 7

        # Specify the default starting octave of the harp, in this case, it's 4 (C4 D4 E4 etc.)
        self.default_starting_octave = 4

        # Compile regexes for notes to save before using
        # these regexes are used for validating whether an individual note is formatted correctly.
        self.note_name_with_octave_regex = None
        self.note_name_regex = None
        self.octave_number_regex = None

    def get_chromatic_scale_dict(self):

        return self.CHROMATIC_SCALE_DICT

    def get_semitone_interval_to_major_scale_interval_dict(self):

        return self.SEMITONE_INTERVAL_TO_MAJOR_SCALE_INTERVAL_DICT

    def get_chromatic_scale_count(self):

        return self.CHROMATIC_SCALE_COUNT

    def get_column_count(self):

        return self.columns

    def get_row_count(self):

        return self.rows

    def get_default_starting_octave(self):

        return self.default_starting_octave

    def get_base_of_western_major_scale(self):

        return self.BASE_OF_MAJOR_SCALE

    def get_note_name_with_octave_regex(self):

        return self.note_name_with_octave_regex

    def get_note_name_regex(self):

        return self.note_name_regex

    def get_octave_number_regex(self):

        return self.octave_number_regex

    def is_valid_note_name_with_octave(self, note):

        '''
        Return True if note is in the format self.note_name_with_octave_regex, e.g. Ab4, else return False
        '''

        note_regexobj = self.get_note_name_with_octave_regex().match(note)

        if note_regexobj:
            return True
        else:
            return False

    def is_valid_note_name(self, note_name):

        '''
        Return True if note is in the format self.note_name_regex, else return False
        '''

        note_regexobj = self.get_note_name_regex().match(note_name)

        if note_regexobj:
            return True
        else:
            return False

    def parse_note(self, note):

        '''
        Returns a tuple containing note_name, octave_number for a note in the format self.note_name_with_octave_regex
        '''

        if self.is_valid_note_name_with_octave(note) == True:
            note_name = self.get_note_name_regex().search(note).group(0)
            #TODO: will probably want to isolate the int() and make this more generic, in the case of Jianpu, octave is denoted by ++ or -- etc.
            octave_number = int(self.get_octave_number_regex().search(note).group(0))
            return (note_name, octave_number)
        else:
            if self.is_valid_note_name(note) == True:

                # Player has given note name without specifying an octave
                note_name = note
                octave_number = self.get_default_starting_octave()
                return (note_name, octave_number)
            else:
                # Raise error, not a valid note
                raise SyntaxError('Note ' + str(note) + ' was not formatted correctly.')

    def convert_note_name_into_chromatic_position(self, note_name):

        '''
        Returns the numeric equivalent of the note in the chromatic scale
        '''

        if self.is_valid_note_name(note_name):
           note_name = self.sanitize_note_name(note_name)
        else:
            #Error: note is not formatted right, output broken harp
            raise SyntaxError('Note ' + str(note_name) + ' was not formatted correctly.')

        chromatic_scale_dict = self.get_chromatic_scale_dict()

        if note_name in chromatic_scale_dict.keys():
            return chromatic_scale_dict[note_name]
        else:
            raise KeyError('Note ' + str(note_name) + ' was not found in the chromatic scale.')

    def convert_semitone_interval_to_major_scale_interval(self, semitone_interval):

        conversion_dict = self.get_semitone_interval_to_major_scale_interval_dict()

        if semitone_interval in conversion_dict.keys():
            return conversion_dict[semitone_interval]
        else:
            raise KeyError('Interval ' + str(semitone_interval) + ' is not in the major scale.')

    def calculate_coordinate_for_note(self, note, song_key='C', note_shift=0):

        '''
        For a note in the format self.note_name_with_octave_regex, this method returns the corresponding coordinate on the Sky piano (in the form of a tuple)

        song_key will be determined by the find_keys method, and is expected to match CHROMATIC_SCALE_DICT, otherwise the default key will be C.
        note_shift is the variable set by the user.

        KeyError will be raised if:
        - note is not in the major scale of song key (using the dict)
        - note is not in the chromatic scale (using the dict)
        SyntaxError will be raised if:
        - note is not formatted correctly

        KeyError and SyntaxError can be caught, by any method that calls this one, to output a broken harp
        '''

        # Convert note to base 7
        note_name, octave_number = self.parse_note(note)

        # Find the major scale interval from the song_key to the note_name
        # Find the semitone interval from the song_key to the note_name first
        if song_key == None:
            song_key = 'C'
        try:
            song_key_chromatic_equivalent = self.convert_note_name_into_chromatic_position(song_key)
        except (KeyError, SyntaxError):
            # default to C major
            song_key_chromatic_equivalent = 0
        try:
            note_name_chromatic_equivalent = self.convert_note_name_into_chromatic_position(note_name)
        except KeyError:
            # will output broken harp
            raise KeyError('Note ' + str(note_name) + ' was not found in the chromatic scale.')
        except SyntaxError:
            raise SyntaxError('Note ' + str(note_name) + ' was not formatted correctly')

        interval_in_semitones = note_name_chromatic_equivalent - song_key_chromatic_equivalent
        if interval_in_semitones < 0:
            # Circular shift the interval back to a positive number, to be used for the SEMITONE_INTERVAL_TO_MAJOR_SCALE_INTERVAL_DICT
            interval_in_semitones += self.get_chromatic_scale_count()

            # The interval_in_semitones is later converted to a major_scale_interval to be used as the 7^0 digit in base 7
            # need to subtract 1 from the octave number after adding an octave to the interval_in_semitones. this is mathematically saying subtracting 3 is the same as adding 4 then taking away 7
            octave_number -= 1

        octave_number_str = self.convert_base_10_to_base_7(octave_number)

        try:
            major_scale_interval = self.convert_semitone_interval_to_major_scale_interval(interval_in_semitones)
        except KeyError:
            # Turn note into a broken harp, since note is not in the song_key
            raise KeyError('Note ' + str(note) + ' is not in the song key.')

        # Convert note to base 10 for arithmetic
        note_in_base_10 = self.convert_base_7_to_base_10(octave_number_str + str(major_scale_interval))

        # shift down, and account for any additional note shift by the player
        note_in_base_10 -= self.get_base_of_western_major_scale()*self.get_default_starting_octave()

        if self.is_valid_note_name_with_octave(note):
            # Skip the note shift if no octave is specified
            note_in_base_10 += note_shift

        # Convert number to base self.columns (using mod and floor), and return as a tuple
        note_coordinate = self.convert_base_10_to_coordinate_of_another_base(note_in_base_10, self.get_column_count())

        if self.is_coordinate_in_range(note_coordinate):
            return note_coordinate
        else:
            # Coordinate is not in range of the two octaves of the Sky piano
            raise KeyError('Note ' + str(note )+ ' is not in range of the two octaves of the Sky piano: ' + str(note_coordinate))
            #TODO: define custom errors

    def convert_base_10_to_base_7(self, num):
        n=3
        numstr = [0]*n
        base = self.get_base_of_western_major_scale()
        for i in range(n-1,-1,-1):
            numstr[i] = int(num/(base**i))
            num -= numstr[i]*(base**i)
        numstr=list(map(str,numstr))
        return ''.join(numstr[::-1]).lstrip('0')


    def convert_base_7_to_base_10(self, num_in_base_7):

        '''
        Given a number in base 7 as a string, returns the number in base 10 as an integer.
        '''

        num_in_base_10 = int(num_in_base_7, self.get_base_of_western_major_scale())
        return num_in_base_10

    def convert_base_10_to_coordinate_of_another_base(self, num, base):

        '''
        Convert a number in base 10 to base `self.columns` (using mod and floor), and return as a tuple
        '''

        remainder = num % base
        quotient = math.floor(num / base)

        return(quotient, remainder)

    def sanitize_note_name(self, note_name):

        # Do any work here to sanitize the note_name so that it matches the keys of self.CHROMATIC_SCALE_DICT

        return note_name

    def is_coordinate_in_range(self, coordinate):

        '''
        Returns True if the coordinate is in range of the Sky piano (as defined by self.columns and self.lines), return False if not.
        coordinate is expected to be a tuple.
        '''

        if coordinate[0] >= 0 and coordinate[0] <= self.get_row_count() - 1 and coordinate[1] >= 0 and coordinate[1] <= self.get_column_count() - 1:
            # Check if the row number and column number of the coordinates are within the instrument's range
            return True
        else:
            return False

class SkyNoteParser(NoteParser):

    def __init__(self):

        super().__init__()

        self.position_map = {
                '.': (-1, -1),
                'A1': (0, 0), 'A2': (0, 1), 'A3': (0, 2), 'A4': (0, 3), 'A5': (0, 4),
                'B1': (1, 0), 'B2': (1, 1), 'B3': (1, 2), 'B4': (1, 3), 'B5': (1, 4),
                'C1': (2, 0), 'C2': (2, 1), 'C3': (2, 2), 'C4': (2, 3), 'C5': (2, 4)
                }

        self.inverse_position_map = {
                (-1, -1): '.',
                (0, 0): 'A1', (0, 1): 'A2', (0, 2): 'A3', (0, 3): 'A4', (0, 4): 'A5',
                (1, 0): 'B1', (1, 1): 'B2', (1, 2): 'B3', (1, 3): 'B4', (1, 4): 'B5',
                (2, 0): 'C1', (2, 1): 'C2', (2, 2): 'C3', (2, 3): 'C4', (2, 4): 'C5'
                }

        self.note_name_with_octave_regex = re.compile(r'([ABCabc][1-5])')
        self.note_name_regex = self.note_name_with_octave_regex
        self.single_note_name_regex = re.compile(r'(\b[ABCabc][1-5]\b)')
        self.not_note_name_regex = re.compile(r'[^ABCabc]+')
        self.not_octave_regex = re.compile(r'[^123]+')


    def calculate_coordinate_for_note(self, note, song_key='C', note_shift=0):
        '''
        Returns a tuple containing the row index and the column index of the note's position.
        '''
        note = note.upper()

        if note in self.position_map.keys(): # Note Shift (ie transposition in Sky)
            pos=self.position_map[note] #tuple
            if (pos[0] < 0) and (pos[1] < 0): #Special character
                return pos
            else:
                idx = pos[0]*self.columns+pos[1]
                idx = idx+note_shift
                pos = (int(idx/self.columns), idx-self.columns*int(idx/self.columns))
                if pos>=(0,0) and pos<=(2,4):
                    return pos
                else:
                    raise KeyError('Note ' + str(note) + ' was not in range of the Sky keyboard.')
        else:
            raise KeyError('Note ' + str(note) + ' was not found in the position_map dictionary.')

    def get_note_from_coordinate(self, coord):

        try:
            note = self.inverse_position_map[coord]
        except KeyError:
            note = 'X'

        return note

    def sanitize_note_name(self, note_name):

        # make sure the first letter of the note is uppercase, for sky note's dictionary keys
        note_name = note_name.capitalize()
        return note_name


class SkyKeyboardNoteParser(SkyNoteParser):

    def __init__(self):

        super().__init__()

        if (os.getenv('LANG') == 'fr') or (os.getenv('LANG') == 'be'):
            self.position_map = {'.': (-1, -1), 'A': (0, 0), 'Z': (0, 1), 'E': (0, 2), 'R': (0, 3), 'T': (0, 4), 'Q': (1, 0), 'S': (1, 1), 'D': (1, 2), 'F': (1, 3), 'G': (1, 4), 'W': (2, 0), 'X': (2, 1), 'C': (2, 2), 'V': (2, 3), 'B': (2, 4)}
            self.keyboard_layout="AZERT QSDFG WXCVB"
        else:
            self.position_map = {'.': (-1, -1), 'Q': (0, 0), 'W': (0, 1), 'E': (0, 2), 'R': (0, 3), 'T': (0, 4), 'A': (1, 0), 'S': (1, 1), 'D': (1, 2), 'F': (1, 3), 'G': (1, 4), 'Z': (2, 0), 'X': (2, 1), 'C': (2, 2), 'V': (2, 3), 'B': (2, 4)}
            self.keyboard_layout="QWERT ASDFG ZXCVB"

        regex = self.keyboard_layout.replace(' ','')
        regex += regex.lower()
        self.note_name_with_octave_regex = re.compile(r'(['+regex+r'])')
        self.note_name_regex = self.note_name_with_octave_regex
        self.single_note_name_regex = re.compile(r'(\b['+regex+r']\b)')
        self.not_note_name_regex = re.compile(r'[^'+regex+r']+')
        self.not_octave_regex = re.compile(r'.')


class EnglishNoteParser(NoteParser):

    def __init__(self):

        super().__init__()

        self.CHROMATIC_SCALE_DICT = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}

        self.inverse_position_map = {
                (0, 0): 'C4', (0, 1): 'D4', (0, 2): 'E4', (0, 3): 'F4', (0, 4): 'G4',
                (1, 0): 'A4', (1, 1): 'B4', (1, 2): 'C5', (1, 3): 'D5', (1, 4): 'E5',
                (2, 0): 'F5', (2, 1): 'G5', (2, 2): 'A6', (2, 3): 'B6', (2, 4): 'C6'
                }

        # Compile regexes for notes to save before using
        self.note_name_with_octave_regex = re.compile(r'([ABCDEFGabcdefg][b#]?\d)')
        self.note_name_regex = re.compile(r'([ABCDEFGabcdefg][b#]?)')
        self.single_note_name_regex = re.compile(r'(\b[ABCDEFGabcdefg][b#]?\d?\b)')
        self.octave_number_regex = re.compile(r'\d')
        self.not_note_name_regex = re.compile(r'[^ABCDEFGabcdefgb#]+')
        self.not_octave_regex = re.compile(r'[^\d]+')

    def sanitize_note_name(self, note_name):
        # make sure the first letter of the note is uppercase, for english note's dictionary keys
        note_name = note_name.capitalize()
        return note_name


    def get_note_from_coordinate(self, coord):

        try:
            note = self.inverse_position_map[coord]
        except KeyError:
            note = 'X'

        return note


class EnglishChordsNoteParser(EnglishNoteParser):

    def __init__(self):

        super().__init__()

        self.english_chords = {
        'C':'C4E4G4', 'D':'D4A4', 'F':'F4A4C5', 'G':'G4B4D5', 'Dm':'D4F4A4', 'Em':'E4G4B4',
        'Am':'A4C5E5', 'Bm':'B4D5', 'Bdim':'B4D5F5', 'A+':'A4C5F5', 'Csus2':'C4D4G4',
        'Dsus2':'C4E4A4', 'Fsus2':'F4G4C5', 'Gsus2':'G4A4D5', 'Asus2':'A4B4E5',
        'Csus4':'C4F4G4', 'Dsus4':'D4G4A4', 'Esus4':'E4A4B4', 'Gsus4':'G4C5D5',
        'Asus4':'A4D5E5', 'D7sus4':'D4G4A4C5', 'E7sus4':'E4A4B4D5', 'G7sus4':'G4C5D5F5',
        'A7sus4':'A4D5E5G5', 'C6':'C4E4G4A4', 'F6':'F4A4C5D5', 'G6':'G4B4D5E5', 'G7':'G4B4D5F5',
        'G9':'G4B4D5F5A5', 'Cmaj7':'C4E4G4B4', 'Fmaj7':'F4A4C5E5', 'Cmaj9':'C4E4G4D5',
        'Fmaj9':'F4A4C5E5G5', 'Cmaj11':'C4E4G4D5F5', 'Dm6':'D4F4A4B4', 'Dm7':'D4F4A4C5',
        'Em7':'E4G4B4D5', 'Am7':'A4C5E5G5', 'Dm9':'D4F4A4C5E5', 'Am9':'A4C5E5G5B5',
        'Dm11':'D4F4A4C5E5G5', 'Am11':'D4A4C5E5G5B5', 'Cmaj':'C4E4G4', 'Dmaj':'D4A4', 'Fmaj':'F4A4C5',
        'Gmaj':'G4B4D5', 'Aaug':'A4C5F5', 'Csus':'C4F4G4', 'Dsus':'D4G4A4', 'Esus':'E4A4B4', 'Gsus':'G4C5D5',
        'Asus':'A4D5E5', 'D7sus':'D4G4A4C5', 'E7sus':'E4A4B4D5', 'G7sus':'G4C5D5F5', 'A7sus':'A4D5E5G5'
        }

        # use EnglishNoteParser as a helper parser for the individual notes
        self.helper_parser = EnglishNoteParser()

    def decode_chord(self, chord):
        '''
            Splits a chord abbreviated name into individual note names
        '''
        chord = self.sanitize_chord_name(chord)
        try:
            return self.english_chords[chord]
        except:
            return chord

    def sanitize_chord_name(self, chord):
         chord = chord.lower().capitalize()
         return chord

    def calculate_coordinate_for_note(self, note, song_key='C', note_shift=0):

        return self.helper_parser.calculate_coordinate_for_note(note, song_key, note_shift)

class DoremiNoteParser(NoteParser):

    def __init__(self):

        super().__init__()

        self.CHROMATIC_SCALE_DICT = {'do': 0, 'do#': 1, 'reb': 1, 're': 2, 're#': 3, 'mib': 3, 'mi': 4, 'fa': 5, 'fa#': 6, 'solb': 6, 'sol': 7, 'sol#': 8, 'lab': 8, 'la': 9, 'la#': 10, 'sib': 10, 'tib': 10, 'si': 11, 'ti': 11}

        self.inverse_position_map = {
                (0, 0): 'do4', (0, 1): 're4', (0, 2): 'mi4', (0, 3): 'fa4', (0, 4): 'sol4',
                (1, 0): 'la4', (1, 1): 'si4', (1, 2): 'do5', (1, 3): 're5', (1, 4): 'mi5',
                (2, 0): 'fa5', (2, 1): 'sol5', (2, 2): 'la6', (2, 3): 'si6', (2, 4): 'do6'
                }

        # Compile regexes for notes to save before using
        self.note_name_with_octave_regex = re.compile(r'([DRMFSLTdrmfslt][OEIAoeia][Ll]?[b#]?\d)')
        self.note_name_regex = re.compile(r'([DRMFSLTdrmfslt][OEIAoeia][Ll]?[b#]?)')
        self.single_note_name_regex = re.compile(r'\b[DRMFSLTdrmfslt][OEIAoeia][Ll]?[b#]?\d?\b')
        self.octave_number_regex = re.compile(r'\d')
        self.not_note_name_regex = re.compile(r'[^DRMFSLTOEIAdrmfsltoeiab#]+')
        self.not_octave_regex = re.compile(r'[^\d]+')

    def sanitize_note_name(self, note_name):

        # make sure the first letter of the note is uppercase, for doremi note's dictionary keys
        note_name = note_name.lower()
        return note_name

    def get_note_from_coordinate(self, coord):

        try:
            note = self.inverse_position_map[coord]
        except KeyError:
            note = 'X'

        return note


class JianpuNoteParser(NoteParser):

    def __init__(self):

        super().__init__()

        self.CHROMATIC_SCALE_DICT = {'1': 0, '1#': 1, '2b': 1, '2': 2, '2#': 3, '3b': 3, '3': 4, '4': 5, '4#': 6, '5b': 6, '5': 7, '5#': 8, '6b': 8, '6': 9, '6#': 10, '7b': 10, '7': 11}

        # Compile regexes for notes to save before using
        self.note_name_with_octave_regex = re.compile(r'([1234567][b#]?[\\+\\-]+)')
        self.note_name_regex = re.compile(r'([1234567][b#]?)')
        self.single_note_name_regex = re.compile(r'\b[1234567][b#]?[\\+\\-]?\b')
        self.octave_number_regex = re.compile(r'[\\+\\-]?')
        self.not_note_name_regex = re.compile(r'[^1234567b#]+')
        self.not_octave_regex = re.compile(r'[^\\+\\-]+')

        self.jianpu2english_map = {
            '1': 'C', '2' : 'D', '3': 'E', '4': 'F', '5': 'G', '6': 'A', '7': 'B',
            'C':'C', 'D':'D', 'E':'E', 'F':'F', 'G':'G', 'A':'A', 'B':'B'
            }

        self.inverse_position_map = {
                (0, 0): '1', (0, 1): '2', (0, 2): '3', (0, 3): '4', (0, 4): '5',
                (1, 0): '6', (1, 1): '7', (1, 2): '1+', (1, 3): '2+', (1, 4): '3+',
                (2, 0): '4+', (2, 1): '5+', (2, 2): '6+', (2, 3): '7+', (2, 4): '1++'
                }

    def get_note_from_coordinate(self, coord):

        try:
            note = self.inverse_position_map[coord]
        except KeyError:
            note = 'X'

        return note


    def parse_note(self, note):

        '''
        Returns a tuple containing note_name, octave_number for a note in the format self.note_name_with_octave_regex
        '''

        note_name = self.note_name_regex.search(note)
        if note_name != None:
            note_name = note_name.group(0)
        else:
            raise KeyError('Note ' + str(note) + ' was not recognized as Jianpu.')

        note_octave = re.search('(\\+)+',note)
        if note_octave != None:
            note_octave = self.get_default_starting_octave()+len(note_octave.group(0))
        else:
            note_octave = re.search('(\\-)+',note)
            if note_octave != None:
                note_octave = self.get_default_starting_octave()-len(note_octave.group(0))
            else:
                note_octave = self.get_default_starting_octave()
        #print(note_base+note_alt+str(note_octave))
        return note_name, note_octave


    def convert_to_english_note(self, note_base, note_alt, note_octave):

        english_note = self.jianpu2english_map[note_base] + note_alt + str(note_octave)

        return english_note
