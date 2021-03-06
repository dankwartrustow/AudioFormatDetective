# Audio Tools, a module and set of tools for manipulating audio data
# Copyright (C) 2007-2015  Brian Langenberger

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


from audiotools import MetaData
import re


class VorbisComment(MetaData):
    ATTRIBUTE_MAP = {'track_name': u'TITLE',
                     'track_number': u'TRACKNUMBER',
                     'track_total': u'TRACKTOTAL',
                     'album_name': u'ALBUM',
                     'artist_name': u'ARTIST',
                     'performer_name': u'PERFORMER',
                     'composer_name': u'COMPOSER',
                     'conductor_name': u'CONDUCTOR',
                     'media': u'SOURCE MEDIUM',
                     'ISRC': u'ISRC',
                     'catalog': u'CATALOG',
                     'copyright': u'COPYRIGHT',
                     'publisher': u'PUBLISHER',
                     'year': u'DATE',
                     'album_number': u'DISCNUMBER',
                     'album_total': u'DISCTOTAL',
                     'comment': u'COMMENT',
                     'compilation': u'COMPILATION'}

    ALIASES = {}

    for aliases in [frozenset([u'TRACKTOTAL', u'TOTALTRACKS']),
                    frozenset([u'DISCTOTAL', u'TOTALDISCS']),
                    frozenset([u'ALBUM ARTIST',
                               u'ALBUMARTIST',
                               u'PERFORMER'])]:
        for alias in aliases:
            ALIASES[alias] = aliases

    def __init__(self, comment_strings, vendor_string):
        """comment_strings is a list of unicode strings

        vendor_string is a unicode string"""

        from audiotools import PY3

        # some debug type checking
        for s in comment_strings:
            assert(isinstance(s, str if PY3 else unicode))
        assert(isinstance(vendor_string, str if PY3 else unicode))

        MetaData.__setattr__(self, "comment_strings", comment_strings)
        MetaData.__setattr__(self, "vendor_string", vendor_string)

    def keys(self):
        return list({comment.split(u"=", 1)[0]
                     for comment in self.comment_strings
                     if (u"=" in comment)})

    def values(self):
        return [self[key] for key in self.keys()]

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def __contains__(self, key):
        from audiotools import PY3
        assert(isinstance(key, str if PY3 else unicode))

        matching_keys = self.ALIASES.get(key.upper(), frozenset([key.upper()]))

        return len([item_value for (item_key, item_value) in
                    [comment.split(u"=", 1) for comment in self.comment_strings
                     if (u"=" in comment)]
                    if (item_key.upper() in matching_keys)]) > 0

    def __getitem__(self, key):
        from audiotools import PY3
        assert(isinstance(key, str if PY3 else unicode))

        matching_keys = self.ALIASES.get(key.upper(), frozenset([key.upper()]))

        values = [item_value for (item_key, item_value) in
                  [comment.split(u"=", 1) for comment in self.comment_strings
                   if (u"=" in comment)]
                  if (item_key.upper() in matching_keys)]

        if len(values) > 0:
            return values
        else:
            raise KeyError(key)

    def __setitem__(self, key, values):
        from audiotools import PY3
        assert(isinstance(key, str if PY3 else unicode))
        for v in values:
            assert(isinstance(v, str if PY3 else unicode))

        new_values = values[:]
        new_comment_strings = []
        matching_keys = self.ALIASES.get(key.upper(), frozenset([key.upper()]))

        for comment in self.comment_strings:
            if u"=" in comment:
                (c_key, c_value) = comment.split(u"=", 1)
                if c_key.upper() in matching_keys:
                    try:
                        # replace current value with newly set value
                        new_comment_strings.append(
                            u"%s=%s" % (c_key, new_values.pop(0)))
                    except IndexError:
                        # no more newly set values, so remove current value
                        continue
                else:
                    # passthrough unmatching values
                    new_comment_strings.append(comment)
            else:
                # passthrough values with no "=" sign
                new_comment_strings.append(comment)

        # append any leftover values
        for new_value in new_values:
            new_comment_strings.append(u"%s=%s" % (key.upper(), new_value))

        MetaData.__setattr__(self, "comment_strings", new_comment_strings)

    def __delitem__(self, key):
        from audiotools import PY3
        assert(isinstance(key, str if PY3 else unicode))

        new_comment_strings = []
        matching_keys = self.ALIASES.get(key.upper(), frozenset([key.upper()]))

        for comment in self.comment_strings:
            if u"=" in comment:
                (c_key, c_value) = comment.split(u"=", 1)
                if c_key.upper() not in matching_keys:
                    # passthrough unmatching values
                    new_comment_strings.append(comment)
            else:
                # passthrough values with no "=" sign
                new_comment_strings.append(comment)

        MetaData.__setattr__(self, "comment_strings", new_comment_strings)

    def __repr__(self):
        return "VorbisComment(%s, %s)" % \
            (repr(self.comment_strings), repr(self.vendor_string))

    def __comment_name__(self):
        return u"Vorbis Comment"

    def raw_info(self):
        """returns a Unicode string of low-level MetaData information

        whereas __unicode__ is meant to contain complete information
        at a very high level
        raw_info() should be more developer-specific and with
        very little adjustment or reordering to the data itself
        """

        from os import linesep
        from audiotools import output_table

        # align text strings on the "=" sign, if any

        table = output_table()

        for comment in self.comment_strings:
            row = table.row()

            if u"=" in comment:
                (tag, value) = comment.split(u"=", 1)
                row.add_column(tag, "right")
                row.add_column(u"=")
                row.add_column(value)
            else:
                row.add_column(comment)
                row.add_column(u"")
                row.add_column(u"")

        return (u"%s:  %s" % (self.__comment_name__(),
                              self.vendor_string) + linesep +
                linesep.join(table.format()))

    def __getattr__(self, attr):
        # returns the first matching key for the given attribute
        # in our list of comment strings

        if attr in self.ATTRIBUTE_MAP:
            key = self.ATTRIBUTE_MAP[attr]

            if attr in {'track_number', 'album_number'}:
                try:
                    # get the TRACKNUMBER/DISCNUMBER values
                    # return the first value that contains an integer
                    for value in self[key]:
                        integer = re.search(r'\d+', value)
                        if integer is not None:
                            return int(integer.group(0))
                    else:
                        # otherwise, return None
                        return None
                except KeyError:
                    # if no TRACKNUMBER/DISCNUMBER, return None
                    return None
            elif attr in {'track_total', 'album_total'}:
                try:
                    # get the TRACKTOTAL/DISCTOTAL values
                    # return the first value that contains an integer
                    for value in self[key]:
                        integer = re.search(r'\d+', value)
                        if integer is not None:
                            return int(integer.group(0))
                except KeyError:
                    pass

                # if no TRACKTOTAL/DISCTOTAL,
                # or none of them contain an integer,
                # look for slashed TRACKNUMBER/DISCNUMBER values
                try:
                    for value in self[{"track_total": u"TRACKNUMBER",
                                       "album_total": u"DISCNUMBER"}[attr]]:
                        if u"/" in value:
                            integer = re.search(r'\d+',
                                                value.split(u"/", 1)[1])
                            if integer is not None:
                                return int(integer.group(0))
                    else:
                        return None
                except KeyError:
                    # no slashed TRACKNUMBER/DISCNUMBER values either
                    # so return None
                    return None
            elif attr == "compilation":
                try:
                    # if present, return True if the first value is "1"
                    return self[key][0] == u"1"
                except KeyError:
                    # if not present, return None
                    return None
            else:
                # attribute is supported by VorbisComment
                try:
                    # if present, return the first value
                    return self[key][0]
                except KeyError:
                    # if not present, return None
                    return None
        elif attr in self.FIELDS:
            # attribute is supported by MetaData
            # but not supported by VorbisComment
            return None
        else:
            # attribute is not MetaData-specific
            return MetaData.__getattribute__(self, attr)

    def __setattr__(self, attr, value):
        # updates the first matching field for the given attribute
        # in our list of comment strings

        def has_number(unicode_string):
            import re

            return re.search(r'\d+', unicode_string) is not None

        def swap_number(unicode_value, new_number):
            import re

            return re.sub(r'\d+', u"%d" % (new_number), unicode_value, 1)

        if (attr in self.FIELDS) and (value is None):
            # setting any value to None is equivilent to deleting it
            # in this high-level implementation
            delattr(self, attr)
        elif attr in self.ATTRIBUTE_MAP:
            key = self.ATTRIBUTE_MAP[attr]

            if attr in {'track_number', 'album_number'}:
                try:
                    current_values = self[key]
                    for i in range(len(current_values)):
                        current_value = current_values[i]
                        if u"/" not in current_value:
                            if has_number(current_value):
                                current_values[i] = swap_number(current_value,
                                                                value)
                                self[key] = current_values
                                break
                        else:
                            (first, second) = current_value.split(u"/", 1)
                            if has_number(first):
                                current_values[i] = u"/".join(
                                    [swap_number(first, value), second])
                                self[key] = current_values
                                break
                    else:
                        # no integer field matching key, so add new one
                        self[key] = current_values + [u"%d" % (value)]
                except KeyError:
                    # no current field with key, so add new one
                    self[key] = [u"%d" % (value)]
            elif attr in {'track_total', 'album_total'}:
                # look for standalone TRACKTOTAL/DISCTOTAL field
                try:
                    current_values = self[key]

                    for i in range(len(current_values)):
                        current_value = current_values[i]
                        if has_number(current_value):
                            current_values[i] = swap_number(current_value,
                                                            value)
                            self[key] = current_values
                            return
                except KeyError:
                    current_values = []

                # no TRACKTOTAL/DISCTOTAL field
                # or none of them contain an integer,
                # so look for slashed TRACKNUMBER/DISCNUMBER values
                try:
                    new_key = {"track_total": u"TRACKNUMBER",
                               "album_total": u"DISCNUMBER"}[attr]
                    slashed_values = self[new_key]

                    for i in range(len(slashed_values)):
                        current_value = slashed_values[i]
                        if u"/" in current_value:
                            (first, second) = current_value.split(u"/", 1)
                            if has_number(second):
                                slashed_values[i] = u"/".join(
                                    [first, swap_number(second, value)])
                                self[new_key] = slashed_values
                                return
                except KeyError:
                    # no TRACKNUMBER/DISCNUMBER field found
                    pass

                # no slashed TRACKNUMBER/DISCNUMBER values either
                # so append a TRACKTOTAL/DISCTOTAL field
                self[key] = current_values + [u"%d" % (value)]
            elif attr == "compilation":
                self[key] = [u"1" if value else u"0"]
            else:
                # leave subsequent fields with the same key as-is
                try:
                    current_values = self[key]
                    self[key] = [value] + current_values[1:]
                except KeyError:
                    # no current field with key, so add new one
                    self[key] = [value]
        elif attr in self.FIELDS:
            # attribute is supported by MetaData
            # but not supported by VorbisComment
            # so ignore it
            pass
        else:
            # attribute is not MetaData-specific, so set as-is
            MetaData.__setattr__(self, attr, value)

    def __delattr__(self, attr):
        #FIXME
        # deletes all matching keys for the given attribute
        # in our list of comment strings

        import re

        if attr in self.ATTRIBUTE_MAP:
            key = self.ATTRIBUTE_MAP[attr]

            if attr in {'track_number', 'album_number'}:
                try:
                    current_values = self[key]

                    # save the _total side of any slashed fields for later
                    slashed_totals = [int(match.group(0)) for match in
                                      [re.search(r'\d+',
                                                 value.split(u"/", 1)[1])
                                       for value in current_values if
                                       u"/" in value]
                                      if match is not None]

                    # remove the TRACKNUMBER/DISCNUMBER field itself
                    self[key] = []

                    # if there are any slashed totals
                    # and there isn't a TRACKTOTAL/DISCTOTAL field already,
                    # add a new one
                    total_key = {'track_number': u"TRACKTOTAL",
                                 'album_number': u"DISCTOTAL"}[attr]

                    if (len(slashed_totals) > 0) and (total_key not in self):
                        self[total_key] = [u"%d" % (slashed_totals[0])]
                except KeyError:
                    # no TRACKNUMBER/DISCNUMBER field to remove
                    pass
            elif attr in {'track_total', 'album_total'}:
                def slash_filter(unicode_string):
                    if u"/" not in unicode_string:
                        return unicode_string
                    else:
                        return unicode_string.split(u"/", 1)[0].rstrip()

                slashed_key = {"track_total": u"TRACKNUMBER",
                               "album_total": u"DISCNUMBER"}[attr]

                # remove TRACKTOTAL/DISCTOTAL fields
                self[key] = []

                # preserve the non-slashed side of TRACKNUMBER/DISCNUMBER fields
                try:
                    self[slashed_key] = [slash_filter(s) for s in
                                         self[slashed_key]]
                except KeyError:
                    # no TRACKNUMBER/DISCNUMBER fields
                    pass
            else:
                # unlike __setattr_, which tries to preserve multiple instances
                # of fields, __delattr__ wipes them all
                # so that orphaned fields don't show up after deletion
                self[key] = []
        elif attr in self.FIELDS:
            # attribute is part of MetaData
            # but not supported by VorbisComment
            pass
        else:
            MetaData.__delattr__(self, attr)

    def __eq__(self, metadata):
        if isinstance(metadata, self.__class__):
            return self.comment_strings == metadata.comment_strings
        else:
            return MetaData.__eq__(self, metadata)

    @classmethod
    def converted(cls, metadata):
        """converts metadata from another class to VorbisComment"""

        from audiotools import VERSION

        if metadata is None:
            return None
        elif isinstance(metadata, VorbisComment):
            return cls(metadata.comment_strings[:],
                       metadata.vendor_string)
        elif metadata.__class__.__name__ == 'FlacMetaData':
            if metadata.has_block(4):
                vorbis_comment = metadata.get_block(4)
                return cls(vorbis_comment.comment_strings[:],
                           vorbis_comment.vendor_string)
            else:
                return cls([], u"Python Audio Tools %s" % (VERSION))
        elif (metadata.__class__.__name__ in ('Flac_VORBISCOMMENT',
                                              'OpusTags')):
            return cls(metadata.comment_strings[:],
                       metadata.vendor_string)
        else:
            comment_strings = []

            for (attr, key) in cls.ATTRIBUTE_MAP.items():
                value = getattr(metadata, attr)
                if value is not None:
                    attr_type = cls.FIELD_TYPES[attr]
                    if attr_type is type(u""):
                        comment_strings.append(
                            u"%s=%s" % (key, value))
                    elif attr_type is int:
                        comment_strings.append(
                            u"%s=%d" % (key, value))
                    elif attr_type is bool:
                        comment_strings.append(
                            u"%s=%d" % (key, 1 if value else 0))

            return cls(comment_strings, u"Python Audio Tools %s" % (VERSION))

    @classmethod
    def supports_images(cls):
        """returns False"""

        # There's actually a (proposed?) standard to add embedded covers
        # to Vorbis Comments by base64 encoding them.
        # This strikes me as messy and convoluted.
        # In addition, I'd have to perform a special case of
        # image extraction and re-insertion whenever converting
        # to FlacMetaData.  The whole thought gives me a headache.

        return False

    def images(self):
        """returns a list of embedded Image objects"""

        return []

    def clean(self):
        """returns a new MetaData object that's been cleaned of problems"""
        from audiotools.text import (CLEAN_REMOVE_TRAILING_WHITESPACE,
                                     CLEAN_REMOVE_LEADING_WHITESPACE,
                                     CLEAN_REMOVE_EMPTY_TAG,
                                     CLEAN_REMOVE_LEADING_WHITESPACE_ZEROES,
                                     CLEAN_REMOVE_LEADING_ZEROES)

        fixes_performed = []
        reverse_attr_map = {}
        for (attr, key) in self.ATTRIBUTE_MAP.items():
            reverse_attr_map[key] = attr
            if key in self.ALIASES:
                for alias in self.ALIASES[key]:
                    reverse_attr_map[alias] = attr

        cleaned_fields = []

        for comment_string in self.comment_strings:
            if u"=" in comment_string:
                (key, value) = comment_string.split(u"=", 1)
                if key.upper() in reverse_attr_map:
                    attr = reverse_attr_map[key.upper()]
                    # handle all text fields by stripping whitespace
                    if len(value.strip()) == 0:
                        fixes_performed.append(
                            CLEAN_REMOVE_EMPTY_TAG %
                            {"field": key})
                    else:
                        fix1 = value.rstrip()
                        if fix1 != value:
                            fixes_performed.append(
                                CLEAN_REMOVE_TRAILING_WHITESPACE %
                                {"field": key})

                        fix2 = fix1.lstrip()
                        if fix2 != fix1:
                            fixes_performed.append(
                                CLEAN_REMOVE_LEADING_WHITESPACE %
                                {"field": key})

                        # integer fields also strip leading zeroes
                        if (((attr == "track_number") or
                             (attr == "album_number"))):
                            match = re.match(r'(.*?)\s*/\s*(.*)', fix2)
                            if match is not None:
                                # fix whitespace/zeroes
                                # on either side of slash
                                fix3 = u"%s/%s" % (
                                    match.group(1).lstrip(u"0"),
                                    match.group(2).lstrip(u"0"))

                                if fix3 != fix2:
                                    fixes_performed.append(
                                        CLEAN_REMOVE_LEADING_WHITESPACE_ZEROES
                                        % {"field": key})
                            else:
                                # fix zeroes only
                                fix3 = fix2.lstrip(u"0")

                                if fix3 != fix2:
                                    fixes_performed.append(
                                        CLEAN_REMOVE_LEADING_ZEROES %
                                        {"field": key})
                        elif ((attr == "track_total") or
                              (attr == "album_total")):
                            fix3 = fix2.lstrip(u"0")
                            if fix3 != fix2:
                                fixes_performed.append(
                                    CLEAN_REMOVE_LEADING_ZEROES %
                                    {"field": key})
                        else:
                            fix3 = fix2

                        cleaned_fields.append(u"%s=%s" % (key, fix3))
                else:
                    cleaned_fields.append(comment_string)
            else:
                cleaned_fields.append(comment_string)

        return (self.__class__(cleaned_fields, self.vendor_string),
                fixes_performed)

    def intersection(self, metadata):
        """given a MetaData-compatible object,
        returns a new MetaData object which contains
        all the matching fields and images of this object and 'metadata'
        """

        def comment_present(comment):
            if u"=" in comment:
                key, value = comment.split(u"=", 1)
                try:
                    for other_value in metadata[key]:
                        if value == other_value:
                            return True
                    else:
                        return False
                except KeyError:
                    return False
            else:
                for other_comment in metadata.comment_strings:
                    if comment == other_comment:
                        return True
                else:
                    return False

        if isinstance(metadata, VorbisComment):
            return self.__class__([comment
                                   for comment in self.comment_strings
                                   if comment_present(comment)],
                                  self.vendor_string)
        else:
            return MetaData.intersection(self, metadata)
