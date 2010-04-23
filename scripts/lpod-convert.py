#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright (c) 2010 Ars Aperta, Itaapy, Pierlis, Talend.
#
# Authors: Hervé Cauwelier <herve@itaapy.com>
#          David Versmisse <david.versmisse@itaapy.com>
#
# This file is part of Lpod (see: http://lpod-project.org).
# Lpod is free software; you can redistribute it and/or modify it under
# the terms of either:
#
# a) the GNU General Public License as published by the Free Software
#    Foundation, either version 3 of the License, or (at your option)
#    any later version.
#    Lpod is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    You should have received a copy of the GNU General Public License
#    along with Lpod.  If not, see <http://www.gnu.org/licenses/>.
#
# b) the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#    http://www.apache.org/licenses/LICENSE-2.0
#

# Import from the standard library
from optparse import OptionParser
from os.path import splitext
from sys import exit

# Import from lpod
from lpod import __version__
from lpod.container import ODF_EXTENSIONS
from lpod.document import odf_get_document, odf_new_document_from_type
from lpod.paragraph import odf_create_paragraph
from lpod.table import odf_create_table, odf_create_row
from lpod.utils import oooc_to_ooow
from lpod.vfs import vfs


class Converter(object):
    # This class exists only to look up functions

    @staticmethod
    def spreadsheet_to_text(indoc, outdoc):
        inbody = indoc.get_body()
        outbody = outdoc.get_body()
        # Copy tables
        for intable in inbody.get_table_list():
            # Skip empty table
            clone = intable.clone()
            clone.rstrip_table()
            if clone.get_table_size() == (0, 0):
                continue
            # At least OOo Writer doesn't like formulas referencing merged
            # cells, so expand
            outtable = odf_create_table(intable.get_table_name(),
                    style=intable.get_table_style())
            # Columns
            for column in intable.traverse_columns():
                outtable.append(column)
            # Rows
            for inrow in intable.traverse_rows():
                outrow = odf_create_row(style=inrow.get_row_style())
                # Cells
                for cell in inrow.traverse_cells():
                    # Formula
                    formula = cell.get_cell_formula()
                    if formula is not None:
                        if formula.startswith('oooc:'):
                            formula = oooc_to_ooow(formula)
                        else:
                            # Found an OpenFormula test case
                            raise NotImplementedError, formula
                        cell.set_cell_formula(formula)
                    outrow.append(cell)
                outtable.append_row(outrow)
            outbody.append(outtable)
            # Separate tables with an empty line
            outbody.append(odf_create_paragraph())
        # Copy styles
        for family in ('table', 'table-column', 'table-row', 'table-cell'):
            for style in indoc.get_style_list(family=family):
                automatic = (style.get_parent().get_tag()
                        == 'office:automatic-styles')
                default = style.get_tag() == 'style:default-style'
                outdoc.insert_style(style, automatic=automatic,
                        default=default)



def get_extension(filename):
    root, ext = splitext(filename)
    # Remove the leading dot
    return ext[1:]



if  __name__ == '__main__':
    # Options initialisation
    usage = "%prog <INFILE> <OUTFILE>"
    description = ("Convert an OpenDocument to another format. "
            "Possible combinations:"
            "    ods -> odt (convert tables and formulas)")
    parser = OptionParser(usage, version=__version__, description=description)
    # Parse !
    opts, args = parser.parse_args()
    # Container
    if len(args) != 2:
        parser.print_help()
        exit(1)
    # Open documents
    infile = args[0]
    indoc = odf_get_document(infile)
    intype = indoc.get_type()
    outfile = args[1]
    extension = get_extension(outfile)
    try:
        mimetype = ODF_EXTENSIONS[extension]
    except KeyError:
        raise ValueError, "output filename not recognized: " + extension
    outtype = mimetype[mimetype.rindex('.') + 1:]
    if '-template' in outtype:
        outtype = mimetype[mimetype.rindex('-') + 1:]
    outdoc = odf_new_document_from_type(outtype)
    # Convert function
    name = '%s_to_%s' % (intype, outtype)
    convertor = getattr(Converter, name, None)
    if convertor is None:
        NotImplementedError, "unsupported combination"
    # Remove output file
    if vfs.exists(outfile):
        vfs.remove(outfile)
    # Convert!
    convertor(indoc, outdoc)
    outdoc.save(outfile)