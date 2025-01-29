import collections
import urllib3
from bs4 import BeautifulSoup
import requests

logfile = open("/var/log/httpd/thetyee.ca.secure-access_log", "r")

clean_log=[]

for line in logfile:
#       print("202 is not in" + line + "\n") 
    try:
        # copy the URLS to an empty list.
        # We get the part between GET and HTTP
        if  (line[line.index("GET")+4:line.index("HTTP")] and '202' in line[line.index("GET")+4:line.index("HTTP")]):
            nline = line[line.index("GET")+4:line.index("HTTP")]
            sline =  nline.split("?")[0]
            if sline.endswith("/"):
                clean_log.append(sline)

    except:
        pass

counter = collections.Counter(clean_log)

# get the Top 50 most popular URLs
for count in counter.most_common(3):
    if '202' not in  str(count[0]):
        continue
#    print(str(count[1]) + "	" + str(count[0]))
    reqs = requests.get("https://thetyee.ca" + str(count[0]))
    soup = BeautifulSoup(reqs.text, 'html.parser')
    title = soup.find_all('title')[0]

    print('<article class="story-item story-item--index-page story-item--minimum">')
    print('<h2 class="story-item__headline"><a href="' + str(count[0]) + '">' + title.get_text().split(' |')[0] + '</a></h2>')
    print ('</article>')


    #print(str(count[0]) + title.get_text())
logfile.close()
