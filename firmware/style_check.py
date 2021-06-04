#!/usr/bin/python3

import os.path
import sys
import re

def check_style_file(fileName):
    # Indent
    indentPattern = re.compile("^(\s+)(.*)")
    multilineCommentIndentPattern = re.compile("^(\t*) \*") # Exception: multiline comments start with " *"
    spacesAsIndentLineNrs = []
    spacesAsIndentLines = []

    # Space after comma
    spaceAfterCommaPattern = re.compile(".*,[^ ]")
    spaceAfterCommaLineNrs = []
    spaceAfterCommaLines = []

    # Space after if etc.
    spaceAfterIfPattern = re.compile(".*(\s|^)(if|switch|for|while)\(")
    spaceAfterIfLineNrs = []
    spaceAfterIfLines = []

    # Space before {
    spaceBeforeCurlyBracketPattern = re.compile(".*([^ ]\{)")
    curlyBracketSwitchCasePattern = re.compile(".*case .*:\{") # Exception: "case bla:{"
    curlyBracketNewlinePattern = re.compile("^\s*\{")  # Exception: "    {"
    curlyBracketPrefixPattern = re.compile("[{(]\{")  # Exception: " {{" or "({" or "//{"
    curlyBrackedCommentedPattern = re.compile("^//\{")  # Exception: "//{"
    spaceBeforeCurlyBracketLineNrs = []
    spaceBeforeCurlyBracketLines = []

    with open(fileName, 'r') as file:
        lines = file.readlines()
        for i in range(0, len(lines)):
            line = lines[i].rstrip('\n')
            lineNr = i + 1

            # Indent
            match = indentPattern.match(line)
            if (match):
                if (' ' in match.group(1)):
                    if (multilineCommentIndentPattern.match(line)):
                        pass
                    else:
                        spacesAsIndentLineNrs.append(lineNr)
                        spacesAsIndentLines.append(line)

            # Space after comma
            match = spaceAfterCommaPattern.match(line)
            if (match):
                spaceAfterCommaLineNrs.append(lineNr)
                spaceAfterCommaLines.append(line)

            # Space after if etc.
            match = spaceAfterIfPattern.match(line)
            if (match):
                spaceAfterIfLineNrs.append(lineNr)
                spaceAfterIfLines.append(line)

            # Space before {
            match = spaceBeforeCurlyBracketPattern.match(line)
            if (match):
                # if (curlyBracketSwitchCasePattern.match(line)):
                #     pass
                if (curlyBracketNewlinePattern.match(line)):
                    pass
                elif (curlyBracketPrefixPattern.match(match.group(1))):
                    pass
                elif (curlyBrackedCommentedPattern.match(line)):
                    pass
                else:
                    spaceBeforeCurlyBracketLineNrs.append(lineNr)
                    spaceBeforeCurlyBracketLines.append(line)

#    print("Checked file", fileName)
    fileName = fileName.split('/')[-1]

    if len(spacesAsIndentLineNrs):
        print("Space as indent on lines:")
        for i in range(0, len(spacesAsIndentLineNrs)):
            print("{}:{}: {}".format(fileName, spacesAsIndentLineNrs[i], spacesAsIndentLines[i]))

    if len(spaceAfterCommaLineNrs):
        print("No space after comma:")
        for i in range(0, len(spaceAfterCommaLineNrs)):
            print("{}:{}: {}".format(fileName, spaceAfterCommaLineNrs[i], spaceAfterCommaLines[i]))

    if len(spaceAfterIfLineNrs):
        print("No space after if:")
        for i in range(0, len(spaceAfterIfLineNrs)):
            print("{}:{}: {}".format(fileName, spaceAfterIfLineNrs[i], spaceAfterIfLines[i]))

    if len(spaceBeforeCurlyBracketLineNrs):
        print("No space before curly bracket:")
        for i in range(0, len(spaceBeforeCurlyBracketLineNrs)):
            print("{}:{}: {}".format(fileName, spaceBeforeCurlyBracketLineNrs[i], spaceBeforeCurlyBracketLines[i]))

    return


def check_style_all(fileNames):
    for fileName in fileNames:
        if (os.path.isfile(fileName)):
            check_style_file(fileName)



fileNames = sys.argv[1:]
check_style_all(fileNames)