murl = "https://www.tripadvisor.com/Hotels-g60763-New_York_City_New_York-Hotels.html"
mL = murl.split("/")
mstr = mL[-1]
lastL= mstr.split("-")
#aList.insert( 3, 2009)
lastL.insert(2,"oa30")

mL[-1]='-'.join(lastL)    
nurl = "/".join(mL)

for i in range(1,25):
    print(f'oa{30*i}')
