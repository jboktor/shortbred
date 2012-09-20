#!/usr/bin/python

#This is a modified version of process_blast.py. That program used "bool" values
#to determine if an amino acid was X'ed out. This program instead records the count
#of regions that overlapped a given AA.

#****************************************************************************
#--Example Use--
#  python process_blast_int.py --fasta /home/jim/tmp/clust.faa --goi /home/jim/tmp/blast_clust_to_clust.txt --ref /home/jim/tmp/blast_clust_to_clust.txt


import re
import sys
import csv
import argparse

import Bio
from Bio.Seq import Seq
from Bio.Alphabet import IUPAC
from Bio.Data import CodonTable
from Bio import SeqIO

parser = argparse.ArgumentParser(description='Remove hits with indetity >=i and length <=l from sequence.')
parser.add_argument('--id',default = .90, type=float, dest='dID', help='Enter the identity cutoff. Examples: .90, .85, .10,...')
parser.add_argument('--len', default = .10, type=float, dest='dL', help='Enter maximum length for region. l=(length hit region)/(length query gene) Examples: .30, .20, .10,... ')
parser.add_argument('--tabs', default = False, type=bool, dest='fTabs', help='Set to True if you would like to print: GeneName, #AAs after process, ##AA initially ')
parser.add_argument('--fasta', type=file, dest='fGOIFasta', help='Enter the path and name of your fasta file.')
parser.add_argument('--abs_l', default=0, type=int, dest='iRegionLength', help='Enter an integer here to remove regions of X length or greater. This will cause the program to ignore any other parameters for length')
parser.add_argument('--ref', type=file, dest='fRefBlast', help='Enter the path and name of the blast results from the refrence db.')
parser.add_argument('--goi', type=file, dest='fGOIBlast', help='Enter the path and name of the blast results from the goi db.')
parser.add_argument('--ko', type=str, dest='sKO', help='Enter \"ref\",\"goi\" or \"both\".')
parser.add_argument('--winlength', type=int, dest='iWinLength', help='Enter window length')

args = parser.parse_args()
             
"""
Add a log file
-Number of genes in input file
-Number of matches in blast file
-Number of unique query genes in blast file
-Number of genes that did not drop any domains
-Number of genes that lost more than 90% of data

"""             
             
dIDcutoff = args.dID * 100
dLengthcutoff = args.dL

###############################################################################
def getGeneData ( fileFasta):
    dictGeneData = {}
    
    for gene in SeqIO.parse(fileFasta, "fasta"):
            dictGeneData.setdefault(gene.id.strip(), str(gene.seq))
        
    
    if dictGeneData.has_key(''):        
        del dictGeneData[''] 
    return dictGeneData

##############################################################################
#Make a dictionary of form (Gene, [0,0,0,0,1,1...]), where the number indicates
#the number of times an amino acid overlaps with a region in the blast output

#Read in the blast output line by line
#When the program finds a new QueryGene:
    #Add the last gene's aiCounts to dictGeneWindows -- (gene, abWindow) 
    #Make a new aiCounts
#When the program finds the same QueryGene:
    #If the region in the blast hit satisfies our length and ID parameters
        #Set the corresponding location in abWindow equal to (count+1)

#Add the last gene when you finish the file

def getOverlapCounts (fileBlast):

    strCurQuery = ""
    dictAAOverlapCounts = {}
    aiCounts =[]
    iGeneCount = 0
    
    for aLine in csv.reader( fileBlast, csv.excel_tab ):
        strQueryID = aLine[0]
        strSubId = aLine[1]
        dIdentity =float(aLine[2])
        iAln= int(aLine[3] )
        iMismatch = int(aLine[4])
        iGap = int(aLine[5] )
        iQStart = int(aLine[6] )
        iQEnd = int(aLine[7])
        iSubStart = int(aLine[8] )
        iSubEnd= int(aLine[9] )
        deVal = float(aLine[10] )
        dBit = float(aLine[11])
        iQLength = int(aLine[12]) 

        if strQueryID != strCurQuery:
            dictAAOverlapCounts.setdefault(strCurQuery, aiCounts)        
            iGeneCount = iGeneCount+1        
            strCurQuery = strQueryID
                  
            
            aiCounts = []
            for i in range(iQLength):
                aiCounts.append(0)
        
        dMatchLength = (iAln) / float(iQLength)


        #If user gave "abs_l" parameter, use that to determine what regions to eliminate
        if (args.iRegionLength>0):
            if (dIdentity >= dIDcutoff) and (iAln >= args.iRegionLength) and (strQueryID!=strSubId):
                #(Blast starts count at 1, but our array starts at 0, so we subtract 1. )                
                for i in range(iQStart-1, iQEnd):
                    aiCounts[i]=aiCounts[i]+1
            
        #Else: Mask high-identity, low-length regions using (alignment length / query length)
        elif (dIdentity >= dIDcutoff) and (dMatchLength <= dLengthcutoff) and (strQueryID!=strSubId):
            for i in range(iQStart-1, iQEnd):
                aiCounts[i]=aiCounts[i]+1
    
    #Once the loop is done, remember to add the last window.
    dictAAOverlapCounts.setdefault(strCurQuery.strip(), aiCounts)        
    iGeneCount = iGeneCount+1 
    
    del dictAAOverlapCounts[""]

    return dictAAOverlapCounts

###########################################################################
#Take the genes in setNames, look in dictKnockOut to see if they have a 
#region of length N without any overlap. Returns set of genes with markers.


def CheckForMarkers(setGenes, dictKnockOut, iN):

    fFoundRegion = False
    fHitEnd = False
    iSumCounts = 0
    iMarkers = 0
    
    setGenesWithMarkers = set()
    
    for key in setGenes:
        aiWindow = dictKnockOut[key]
        iStart = 0
        while (fFoundRegion == False and fHitEnd == False):
            if ((iStart+iN) > len(aiWindow)):
                fHitEnd = True
            iSumCounts = sum(aiWindow[iStart:(iStart+iN)])        
            if (iSumCounts == 0 and fHitEnd==False):
                iMarkers +=1
                fFoundRegion = True
                setGenesWithMarkers.add(key)
            iStart += 1
        fFoundRegion = False
        fHitEnd = False
    
    return setGenesWithMarkers
###############################################################################
def CheckForQuasiMarkers(setGenes, dictKnockOut, dictGenes, iN):
    
    #Only run this on the leftover genes
    #For each one, sum up the values from [0:n], then [1:n+1]...
    #Store these in an array of length (genelength-n)
    #FInd the minimum value in this array
    #Take its index
    #Your window is [index:index+n]
    
    #Get the appropriate string from dictGOIgenes    
    #add it to dictQM
    
    
    #Return dictQM with these windows

    dictQM = {}

    
    
    
    
    setGenesWithMarkers = set()
    
    for key in setGenes:
        aiWindow = dictKnockOut[key]
        iStart = 0
        fHitEnd = False
        iMin = 0
        iSumCounts = 0
        aiWindowSums = []
        #print aiWindow
        

        
        #Cycle through all windows of length N, record total overlap
        
        while (fHitEnd == False):
            if ((iStart+iN) >= len(aiWindow)):
                fHitEnd = True                
            iSumCounts = sum(aiWindow[iStart:(iStart+iN)])        
            aiWindowSums.append(iSumCounts)
            iStart+=1
            
        iMin = min(aiWindowSums)
        iWinStart = aiWindowSums.index(iMin)            
        
        dictQM[key]= [dictGenes[key][iWinStart:iWinStart+iN],iMin]
        
        
        #Error Checking   
        """             
        if (key == "VFG1266" or key == "VFG0696" or key=="VFG2059"): 
            print key
            print dictRefCounts.get(key,"Not in Ref Blast Results")
            print dictGOICounts.get(key,"Not in Clust Blast Results")
            print dictGOIGenes[key]
            print aiWindowSums

            print iMin, iWinStart
            
            print dictGenes[key][iWinStart:iWinStart+iN]
        """
        
    
    return dictQM


##############################################################################
#Get dict of GeneSeqs, then overlap counts from the Ref and GOI blast results
dictGOIGenes = getGeneData(args.fGOIFasta)
dictRefCounts = getOverlapCounts(args.fRefBlast)
dictGOICounts = getOverlapCounts(args.fGOIBlast)

print "GOI Genes:", len(dictGOIGenes)
print "Ref Valid Hits:", len(dictRefCounts)
print "GOI Valid Hits:",len(dictGOICounts)

#If a gene has 0 valid hits in the ref database, make an array of 0's
#so the program knows that nothing overlapped with the gene
setGOINotInRef = set(dictGOIGenes.keys()).difference(set(dictRefCounts.keys()))

if len(setGOINotInRef)>0:
    for sGene in setGOINotInRef:
        dictRefCounts[sGene] = [0]*len(dictGOIGenes[sGene])

#If a gene has 0 valid hits in the GOI database (unlikely), make an 
#array of 0's so the program knows that nothing overlapped with the gene    

setGOINoHits = set(dictGOIGenes.keys()).difference(set(dictGOICounts.keys()))

if len(setGOINoHits)>0:
    for sGene in setGOINoHits:
        dictGOICounts[sGene] = [0]*len(dictGOIGenes[sGene])


#Get dict of counts for (Ref+GOI)
dictBoth = {}
setRefGOI = set(dictGOICounts.keys()).union(set(dictRefCounts.keys())) 

for sGene in setRefGOI:
    aiSum =[sum(aiCounts) for aiCounts in zip(dictGOICounts.get(sGene,[0]),dictRefCounts.get(sGene,[0]))]
    dictBoth[sGene] = aiSum
    


###########################################################################
#Check for genes that have "marker windows": windows of length N that do not
#overlap with anything in the "overlap reference"

print ""
print "Window Length: ", args.iWinLength

setHasMarkers = CheckForMarkers(set(dictGOIGenes.keys()).intersection(dictBoth.keys()), dictBoth, args.iWinLength)
print "Genes with True Markers:", len(setHasMarkers)

setLeftover = set(dictGOIGenes.keys()).difference(setHasMarkers)

setHasClassMarkers = CheckForMarkers(setLeftover.intersection(dictRefCounts.keys()), dictRefCounts, args.iWinLength)
print "Genes with Class Markers:",  len(setHasClassMarkers)


setLeftover = setLeftover.difference(setHasClassMarkers)

dictQuasiMarkers = CheckForQuasiMarkers(setLeftover, dictBoth, dictGOIGenes,args.iWinLength)
print "Genes with Quasi-Markers:", len(dictQuasiMarkers)

print "Union of all Genes with Markers:", len((setHasMarkers.union(setHasClassMarkers)).union(dictQuasiMarkers.keys()))


###########################################################################
#Replace AA's with X's in True Markers
for key in setHasMarkers:
        if dictBoth.has_key(key):
            aiWindow = dictBoth[key]
            strGene = list(dictGOIGenes[key])

            for i in range(0,len(aiWindow)):
                if aiWindow[i] >= 1:
                    strGene[i] = "X"
            strGene = "".join(strGene)
            dictGOIGenes[key] =strGene

###########################################################################
#Replace AA's with X's in Class Markers
for key in setHasClassMarkers:
        if dictRefCounts.has_key(key):
            aiWindow = dictRefCounts[key]
            strGene = list(dictGOIGenes[key])

            for i in range(0,len(aiWindow)):
                if aiWindow[i] >= 1:
                    strGene[i] = "X"
            strGene = "".join(strGene)
            dictGOIGenes[key] =strGene
            
###########################################################################
#Add in the QuasiMarkers

for key in dictQuasiMarkers:
    dictGOIGenes[key]=dictQuasiMarkers[key][0]
   
##############################################################################
#Print out the genes
strGeneName = ""
iCount = 0

print "Length of dictGOIGenes:",len(dictGOIGenes)
     
for key in dictGOIGenes:
    if key in setHasMarkers:
        strGeneName = ">" + key + "_TM"
    elif key in setHasClassMarkers:
        strGeneName = ">" + key + "_CM"
    elif key in dictQuasiMarkers:
        strGeneName = ">" + key + "_QM" + str(dictQuasiMarkers[key][1])
    else:
        strGeneName = ">" + key + "_OTH"
         
    
    print strGeneName
    print re.sub("(.{80})","\\1\n",dictGOIGenes[key],re.DOTALL)
    iCount = iCount+1