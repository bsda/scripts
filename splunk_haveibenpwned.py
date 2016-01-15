#!/usr/bin/env python

import sys
import json
import csv
import urllib2
import string
import socket

email = sys.argv[1]

def check_dump(email):
  try:
    url = 'http://haveibeenpwned.com/api/v2/breachedaccount/'
    req = url + str(email) #+ str('?truncateResponse=true')
    r = urllib2.urlopen(req)
    if r.getcode() == 404:
      x = ''
      return x
    if r.getcode()== 200:
      j = json.load(r) 
      z = list()
      for n in j:
         z.append(n['Domain']) 
      return '|'.join(z) 
    else:
      pass
  except Exception as e:
    x = ''
    return x

def check_paste(email):
  try:
    url = 'http://haveibeenpwned.com/api/v2/pasteaccount/'
    req = url + str(email)
    r = urllib2.urlopen(req)
    if r.getcode() == 404:
      x = ''
      return x
    if r.getcode()== 200:
      j = json.load(r)
      z = list()
      for i in j:
          z.append(i['Source'] + ':' + i['Id'])

      return '|'.join(z)
    else:
      pass
  except Exception as e:
    x = ''
    return x



def main():


   infile = sys.stdin
   outfile = sys.stdout
   
   r = csv.DictReader(infile)
   header = r.fieldnames

   fields = ["email","pwned","pwn_dump","pwn_paste"]
   w = csv.DictWriter(outfile, fieldnames=fields)
   w.writeheader()

   for result in r:
      
      dump = check_dump(result['email'])
      paste = check_paste(result['email'])

      if dump != ''  or paste != '':
         pwned = 'yes'
      else:
         pwned = 'no'

      output = csv.writer(sys.stdout)
      data = [result['email'],pwned,dump,paste]
      output.writerow(data)

main()

