__author__ = 'isha'

import random
import numpy as np
import scipy as sp
import pandas as pd
from sklearn import datasets as skldatasets
import matplotlib.pyplot as plt

if __name__ == '__main__':
    print "Hello Random World", random.random(), np.random.random()

    series = pd.Series([1, 5, np.nan, 23, 157])
    print "Series"
    print series

    series = series.fillna(value=15)
    print "Series after handling missing data"
    print series

    series = series.cumsum()
    print "New series"
    print series

    print "Plotting"
    plt.figure()
    series.plot()
    plt.legend(loc='best')
    plt.show(block=True)
    plt.interactive(False)

    dates = pd.date_range('20150101', periods=8)
    print "Dates"
    print dates

    dataframe = pd.DataFrame(np.random.randn(8, 4), index=dates, columns=list('ABCD'))
    print "Dataframe head"
    print dataframe.head()
    print "Dataframe tail"
    print dataframe.tail()
    print "Dataframe index"
    print dataframe.index

    digits = skldatasets.load_digits()
    print "Scikit learn digits dataset\n", digits.data

    print "SciPy info"
    print sp.info()
