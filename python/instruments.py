import os
import notes

try:
    from PIL import Image, ImageDraw, ImageFont

    no_PIL_module = False
except (ImportError, ModuleNotFoundError):
    no_PIL_module = True

try:
    import mido

    no_mido_module = False
except (ImportError, ModuleNotFoundError):
    no_mido_module = True


# ## Instrument classes

class Instrument:

    def __init__(self, maker):
        self.type = 'undefined'
        self.chord_skygrid = {}
        self.repeat = 1
        self.index = 0
        self.is_silent = True
        self.is_broken = False
        self.maker = maker
        self.directory_base = self.maker.get_directory_base()
        self.directory_elements = os.path.join(self.directory_base, 'elements')
        self.directory_fonts = os.path.join(self.directory_base, 'fonts')
        self.empty_chord_png = os.path.normpath(os.path.join(self.directory_elements, 'empty-chord.png'))  # blank harp
        self.unhighlighted_chord_png = os.path.normpath(os.path.join(self.directory_elements,
                                                                     'unhighlighted-chord.png'))  # harp with unhighlighted notes
        self.broken_png = os.path.normpath(os.path.join(self.directory_elements, 'broken-symbol.png'))
        self.silent_png = os.path.normpath(os.path.join(self.directory_elements, 'silent-symbol.png'))
        self.png_chord_size = None
        self.text_bkg = (255, 255, 255, 0)  # Transparent white
        self.song_bkg = (255, 255, 255)  # White paper sheet
        self.font_color = (0, 0, 0)
        self.font = os.path.normpath(os.path.join(self.directory_fonts, 'NotoSansCJKjp-Regular.otf'))
        self.font_size = 38
        self.repeat_height = None

        self.midi_relspacing = 0.1  # Spacing between midi notes, as a ratio of note duration
        self.midi_pause_relduration = 1  # Spacing between midi notes, as a ratio of note duration
        self.midi_quaver_relspacing = 0.5

    def get_maker(self):

        return self.maker

    def set_chord_skygrid(self, chord_skygrid):
        self.chord_skygrid = chord_skygrid

    def get_chord_skygrid(self):
        """Returns the dictionary for the chord:
            where each key is the note position (tuple of row/index),
            the value is a dictionary with key=frame, value=True/False,
            where True/False means whether the note is played or not.
            Inactive notes are actually not in the dictionary at all.
            Example: {(0,0):{0:True}, (1,1):{0:True}}
        """
        return self.chord_skygrid

    def get_type(self):
        return self.type

    def get_directory_base(self):
        return self.directory_base
        
    def get_directory_elements(self):
        return self.directory_elements
        
    def get_directory_font(self):
        return self.directory_fonts
        
    def set_repeat(self, repeat):
        self.repeat = repeat

    def get_repeat(self):
        """Returns the number of times the chord must be played"""
        return self.repeat

    def set_index(self, index):
        self.index = index

    def get_index(self):
        """Instrument index in the song"""
        return self.index

    def get_is_silent(self):
        """Returns whether the Harp is empty of notes (silent)"""
        return self.is_silent

    def get_is_broken(self):
        """Returns whether the Harp is broken (notes were not recognized by the Parser)"""
        return self.is_broken

    def set_is_broken(self, is_broken=True):
        """Returns a boolean whether the harp could be translated"""
        self.is_broken = is_broken

    def set_is_silent(self, is_silent=True):
        """Returns a boolean whether the harp is empty in this frame"""
        self.is_silent = is_silent

    def set_png_chord_size(self):
        """ Sets the size of the chord image from the .png file """
        if self.png_chord_size is None:
            self.png_chord_size = Image.open(self.unhighlighted_chord_png).size

    def get_png_chord_size(self):
        """ Returns the size of the chord image, or sets it if None """
        if self.png_chord_size is None:
            self.set_png_chord_size()
        return self.png_chord_size

    def get_repeat_png(self, max_rescaled_width, rescale=1):
        """Returns an image of the repeat number xN"""
        repeat_im = Image.new('RGBA', (int(max_rescaled_width / rescale), int(self.get_png_chord_size()[1])),
                              color=self.text_bkg)
        draw = ImageDraw.Draw(repeat_im)
        fnt = ImageFont.truetype(self.font, self.font_size)
        draw.text((0, repeat_im.size[1] - 1.05 * fnt.getsize(str(self.repeat))[1]), 'x' + str(self.repeat), font=fnt,
                  fill=self.font_color)

        if rescale != 1:
            repeat_im = repeat_im.resize((int(repeat_im.size[0] * rescale), int(repeat_im.size[1] * rescale)),
                                         resample=Image.LANCZOS)

        return repeat_im


class Voice(Instrument):  # Lyrics or comments

    def __init__(self, maker):
        super().__init__(maker)
        self.type = 'voice'
        self.lyric = ''
        # self.text_bkg = (255, 255, 255, 0)#Uncomment to make it different from the inherited class
        # self.font_color = (255,255,255)#Uncomment to make it different from the inherited class
        # self.font = 'fonts/NotoSansCJKjp-Regular.otf'
        self.font_size = 32
        self.lyric_height = None
        self.lyric_width = None

    def render_in_html(self, note_width):
        """Renders the lyrics text in HTML inside an invisible table"""
        chord_render = '<table class=\"voice\">'
        chord_render += '<tr>'
        chord_render += '<td>'
        chord_render += self.lyric
        chord_render += '</td>'
        chord_render += '</tr>'
        chord_render += '</table>'
        return chord_render

    def get_lyric(self):
        return self.lyric

    def set_lyric(self, lyric):
        self.lyric = lyric

    def __len__(self):
        return len(self.lyric)

    def __str__(self):
        return '<' + self.type + '-' + str(self.index) + ', ' + str(len(self)) + ' chars, repeat=' + str(
            self.repeat) + '>'

    def render_in_ascii(self, render_mode):
        chord_render = '#' + self.lyric + ' '  # Lyrics marked as comments in output text files
        return chord_render

    def get_lyric_height(self):
        """Calculates the height of the lyrics based on a standard text and the font size"""
        if self.lyric_height is None:
            fnt = ImageFont.truetype(self.font, self.font_size)
        return fnt.getsize('HQfgjyp')[1]

    def render_in_svg(self, x, width, height, aspect_ratio):
        """Renders the lyrics text in SVG"""
        voice_render = '\n<svg x=\"' + '%.2f' % x + '\" y=\"0\" width=\"100%\" height=\"' + height + '\" class=\"voice voice-' + str(
            self.get_index()) + '\">'
        voice_render += '\n<text x=\"0%\" y=\"50%\" class=\"voice voice-' + str(
            self.get_index()) + '\">' + self.lyric + '</text>'
        voice_render += '\n</svg>'
        return voice_render

    def render_in_png(self, rescale=1.0):
        """Renders the lyrics text in PNG"""
        chord_size = self.get_png_chord_size()
        fnt = ImageFont.truetype(self.font, int(self.font_size))
        lyric_width = fnt.getsize(self.lyric)[0]
        
        lyric_im = Image.new('RGBA', (int(max(chord_size[0],lyric_width)), int(self.get_lyric_height())), color=self.text_bkg)
        draw = ImageDraw.Draw(lyric_im)
        
        if lyric_width < chord_size[0]:
            #Draws centered text
           draw.text((int((chord_size[0] - lyric_width) / 2.0), 0), self.lyric, font=fnt, fill=self.font_color)
        else:
            #Draws left-aligned text that spilles over the next icon
           draw.text((0, 0), self.lyric, font=fnt, fill=self.font_color)

        if rescale != 1:
            lyric_im = lyric_im.resize((int(lyric_im.size[0] * rescale), int(lyric_im.size[1] * rescale)),
                                       resample=Image.LANCZOS)
        return lyric_im


class Harp(Instrument):

    def __init__(self, maker):
        super().__init__(maker)
        self.type = 'harp'
        self.column_count = 5
        self.row_count = 3

    def get_row_count(self):
        return self.row_count

    def get_column_count(self):
        return self.column_count

    def get_num_highlighted(self):
        num = 0
        for k in self.chord_skygrid.keys():
            for kk in self.chord_skygrid[k].keys():
                if self.chord_skygrid[k][kk]:
                    num += 1
        return num

    def __len__(self):
        return self.column_count * self.row_count

    def __str__(self):
        return '<' + self.type + '-' + str(self.index) + ', ' + str(len(self)) + ' notes, ' + \
               str(self.get_num_highlighted()) + ' highlighted, repeat=' + str(self.repeat) + '>'

    def get_note_from_position(self, pos):
        """Returns the note type Root, Diamond, Circle from the position in Sky grid"""
        # Calculate the note's overall index in the harp (0 to 14)              
        note_index = (pos[0] * self.get_column_count()) + pos[1]

        if note_index % 7 == 0:  # the 7 comes from the heptatonic scale of Sky's music (no semitones)
            # Note is a root note
            return notes.NoteRoot(self, pos)  # very important: the chord creating the note is passed as a parameter
        elif (
                note_index % self.get_column_count % 2 == 0:
            # Note is in an odd column, so it is a circle
            return notes.NoteCircle(self, pos)
        else:
            # Note is in an even column, so it is a diamond
            return notes.NoteDiamond(self, pos)

    def render_in_ascii(self, note_parser):

        ascii_chord = ''

        if self.get_is_broken():
            ascii_chord = 'X'
        elif self.get_is_silent():
            ascii_chord = '.'
        else:
            chord_skygrid = self.get_chord_skygrid()
            for k in chord_skygrid:  # Cycle over positions in a frame
                for f in chord_skygrid[k]:  # Cycle over triplets & quavers
                    if chord_skygrid[k][f]:  # Button is highlighted
                        ascii_chord += note_parser.get_note_from_coordinate(k)
        return ascii_chord

    def render_in_html(self, note_width):

        harp_silent = self.get_is_silent()
        harp_broken = self.get_is_broken()

        if harp_broken:
            class_suffix = 'broken'
        elif harp_silent:
            class_suffix = 'silent'
        else:
            class_suffix = ''

        harp_render = '<table class=\"harp harp-' + str(self.get_index()) + ' ' + class_suffix + '">'

        for row in range(self.get_row_count()):

            harp_render += '<tr>'

            for col in range(self.get_column_count()):
                harp_render += '<td>'

                note = self.get_note_from_position((row, col))

                note_render = note.render_in_html(note_width)
                harp_render += note_render
                harp_render += '</td>'

            harp_render += '</tr>'

        harp_render += '</table>'

        if self.get_repeat() > 1:
            harp_render += '<table class=\"harp-' + str(self.get_index()) + ' repeat\">'
            harp_render += '<tr>'
            harp_render += '<td>'
            harp_render += 'x' + str(self.get_repeat())
            harp_render += '</td>'
            harp_render += '</tr>'
            harp_render += '</table>'

        return harp_render

    def render_in_svg(self, x, harp_width, harp_height, aspect_ratio):

        harp_silent = self.get_is_silent()
        harp_broken = self.get_is_broken()

        if harp_broken:
            class_suffix = 'broken'
        elif harp_silent:
            class_suffix = 'silent'
        else:
            class_suffix = ''

        # The chord SVG container
        harp_render = '\n<svg x=\"' + '%.2f' % x + '\" y=\"0\" width=\"' + harp_width + '\" height=\"' + harp_height + '\" class=\"instrument-harp harp-' + str(
            self.get_index()) + ' ' + class_suffix + '\">'

        # The chord rectangle with rounded edges
        harp_render += '\n<rect x=\"0.7%\" y=\"0.7%\" width=\"98.6%\" height=\"98.6%\" rx=\"7.5%\" ry=\"' + '%.2f' % (
                7.5 * aspect_ratio) + '%\" class=\"harp harp-' + str(self.get_index()) + '\"/>'

        for row in range(self.get_row_count()):
            for col in range(self.get_column_count()):
                note = self.get_note_from_position((row, col))
                # note.set_position(row, col)

                note_width = 0.21
                xn = 0.12 + col * (1 - 2 * 0.12) / (self.get_column_count() - 1) - note_width / 2.0
                yn = 0.15 + row * (1 - 2 * 0.16) / (self.get_row_count() - 1) - note_width / 2.0

                # NOTE RENDER
                note_render = note.render_in_svg('%.2f' % (100 * note_width) + '%', '%.2f' % (100 * xn) + '%',
                                                 '%.2f' % (100 * yn) + '%')

                harp_render += note_render

        harp_render += '</svg>'

        return harp_render

    def render_in_png(self, rescale=1.0):
        def trans_paste(bg, fg, box=(0, 0)):
            if fg.mode == 'RGBA':
                if bg.mode != 'RGBA':
                    bg = bg.convert('RGBA')
                fg_trans = Image.new('RGBA', bg.size)
                fg_trans.paste(fg, box, mask=fg)  # transparent foreground
                return Image.alpha_composite(bg, fg_trans)
            else:
                if bg.mode == 'RGBA':
                    bg = bg.convert('RGB')
                bg.paste(fg, box)
                return bg

        harp_silent = self.get_is_silent()
        harp_broken = self.get_is_broken()

        harp_file = Image.open(self.unhighlighted_chord_png)  # loads default harp image into memory
        harp_size = harp_file.size

        harp_render = Image.new('RGB', harp_file.size, self.song_bkg)  # Empty image

        # Get a typical note to check that the size of the note png is consistent with the harp png                  
        note_size = notes.Note(self).get_png_size()
        note_rel_width = note_size[0] / harp_size[0]  # percentage of harp
        if note_rel_width > 1.0 / self.get_column_count() or note_rel_width < 0.05:
            note_rescale = 0.153 / note_rel_width
        else:
            note_rescale = 1

        if harp_broken:  # '?' in the middle of the image (no harp around)
            symbol = Image.open(self.broken_png)
            harp_render = trans_paste(harp_render, symbol, (
                int((harp_size[0] - symbol.size[0]) / 2.0), int((harp_size[1] - symbol.size[1]) / 2.0)))
        elif harp_silent:  # '.' in the middle of the image (no harp around)
            symbol = Image.open(self.silent_png)
            harp_render = trans_paste(harp_render, symbol, (
                int((harp_size[0] - symbol.size[0]) / 2.0), int((harp_size[1] - symbol.size[1]) / 2.0)))
        else:
            harp_render = trans_paste(harp_render, harp_file)  # default harp image
            for row in range(self.get_row_count()):
                for col in range(self.get_column_count()):

                    note = self.get_note_from_position((row, col))
                    # note.set_position(row, col)

                    # NOTE RENDER
                    if len(note.get_highlighted_frames()) > 0:  # Only paste highlighted notes
                        xn = (0.13 + col * (1 - 2 * 0.13) / (self.get_column_count() - 1)) * harp_size[0] - note_size[
                            0] / 2.0
                        yn = (0.17 + row * (1 - 2 * 0.17) / (self.get_row_count() - 1)) * harp_size[1] - note_size[
                            1] / 2.0
                        note_render = note.render_in_png(note_rescale)
                        harp_render = trans_paste(harp_render, note_render, (int(round(xn)), int(round(yn))))

        if rescale != 1:
            harp_render = harp_render.resize((int(harp_render.size[0] * rescale), int(harp_render.size[1] * rescale)),
                                             resample=Image.LANCZOS)

        return harp_render

    def render_in_midi(self, note_duration=960, music_key='C'):
        harp_silent = self.get_is_silent()
        harp_broken = self.get_is_broken()

        if harp_broken:
            harp_render = [
                mido.Message('note_on', note=115, velocity=127, time=int(self.midi_relspacing * note_duration)),
                mido.Message('note_off', note=115, velocity=127, time=int(self.midi_relspacing * note_duration))]
        elif harp_silent:
            harp_render = [
                mido.Message('note_on', note=115, velocity=0, time=int(self.midi_relspacing * note_duration)),
                mido.Message('note_off', note=115, velocity=0, time=int(self.midi_pause_relduration * note_duration))]
        else:
            harp_render = []
            durations = [self.midi_relspacing * note_duration, note_duration]
            for i, event_type in enumerate(['note_on', 'note_off']):
                t = durations[i]
                for row in range(self.get_row_count()):
                    for col in range(self.get_column_count()):
                        note = self.get_note_from_position((row, col))
                        frames = note.get_highlighted_frames()

                        note_render = note.render_in_midi(event_type, t, music_key)

                        if isinstance(note_render, mido.Message):
                            harp_render.append(note_render)
                            # Below a complicated way to handle quavers
                            if frames[0] == 0 or event_type == 'note_off':
                                t = 0
                            elif frames[0] > 0 and event_type == 'note_on':
                                t = durations[0] + durations[1]
                            else:
                                t = durations[i]

        return harp_render

