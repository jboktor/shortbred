#!/usr/bin/python
import Bio
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.Data import CodonTable
from Bio import SeqIO

import sys
import re
import argparse

parser = argparse.ArgumentParser(description='Takes a fasta file with conserved regions X\'ed out, and makes windows.')
parser.add_argument('-WinLength', default = 20, type=int, dest='iMinWinLength', help='Enter the minimum length for individual windows. Default is 30')
parser.add_argument('-TotLength', default = 200, type=int, dest='iTotLength', help='Enter the maximum length for the combined windows for a gene. Default is 200')
args = parser.parse_args()

"""
This program takes a fasta file with regions X'ed out and produces windows.
"""
###########################################################
#Load windows into a dictionary of the form (gene, [window])
def getGeneWindows ( fileFasta):
    dictGeneData = {}
    
    for gene in SeqIO.parse(fileFasta, "fasta"):
        #Ignore the suffixes at end of gene name, e.g. "_#04"         
        mtchName = re.search(r'(.*)(\_\#[0-9]*)',gene.id)
        if mtchName:
            strName = mtchName.group(1)        
        else:
            strName = gene.id
        
        #If gene is already in dict, append window to the gene's entry
        #   else - add (gene, [window]) to dict        
        
        if strName in dictGeneData.keys():
            dictGeneData[strName].append(str(gene.seq))
            
        else:
            dictGeneData[strName] = []
            dictGeneData[strName].append(str(gene.seq))
 
    return dictGeneData
############################################################
#Loop through dict of form: (gene, [window1, window2, ...])
#Split windows with X's into new windows
#Split windows longer than the maximum length into smaller windows

def splitGenes(dictGeneData):
    astrNewWindows = []
    
    for strName in dictGeneData.keys():
        astrNewWindows = []
        
        #Split by the X's        
        for strOldWindow in dictGeneData[strName]:
            for strNewWindow in (re.split('X*',strOldWindow)):
                astrNewWindows.append(strNewWindow)
        dictGeneData[strName] = astrNewWindows
        
        #Cut windows over TotLength into smaller windows
        astrNewWindows = []        
        for strWindow in dictGeneData[strName]:
            while (len(strWindow)>args.iTotLength):
                strNewWindow = strWindow[:args.iTotLength]
                astrNewWindows.append(strNewWindow)
                strWindow = strWindow[args.iTotLength:]
            astrNewWindows.append(strWindow)
        dictGeneData[strName] = astrNewWindows        
                
            
    
    return dictGeneData
            
############################################################
#Loop through dict of form: (gene, [window1, window2, ...])
#   For each entry, loop through [window1,window2,...]
#       Print windows that fit criteria (-WinLength and iTotLength)
#       Add suffix indicating window number _#01, _#02


def printWindows(dictGeneData):
    for strName in dictGeneData.keys():
        iCounter = 0
        iLength = 0
        for strWindow in dictGeneData[strName]:
                if  (len(strWindow) >= args.iMinWinLength) and ((iLength + len(strWindow)) <=  args.iTotLength):
                     iCounter = iCounter +1
                     print ">" + strName + "_#" + str(iCounter).zfill(2)
                     print re.sub("(.{80})","\\1\n",strWindow,re.DOTALL)
                     iLength = iLength + len(strWindow)
    return                    
                    
##############################################################
dictGeneWindows = getGeneWindows (sys.stdin)
dictSplitWindows = splitGenes(dictGeneWindows)
printWindows(dictSplitWindows)
