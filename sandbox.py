__author__ = 'isha'

def copySubdirectoryContentsToParent(directory, suffixOfInterest):
    import os
    print "Running for directory {}".format(directory)
    #print "\n".join(["{} {} {}".format(x[0], x[1], x[2]) for x in os.walk(directory)])
    for d in os.walk(directory):
        for subdirname in d[1]:
            if subdirname.endswith(suffixOfInterest):
                subdir = os.path.join(directory, subdirname)
                for element in os.walk(subdir):
                    for subfilename in element[2]:
                        subfile = os.path.join(subdir, subfilename)
                        newsubfile = os.path.join(directory, subfilename)
                        print "Moving {} to {}".format(subfile, newsubfile)
                        os.rename(subfile, newsubfile)
        break


if __name__ == '__main__':
    copySubdirectoryContentsToParent('/Users/isha/workspace/sandbox/kaggle/input/shapefiles/pums', 'puma10')