import matplotlib.pyplot as plt
from ebcli.lib.utils import urllib
from math import sqrt
from matplotlib import gridspec
from matplotlib.pylab import gca
import matplotlib.dates as mdates
import json
import matplotlib.patches as mpatches


import numpy as np
import pymysql
from matplotlib.lines import Line2D

import fit
import segment

plt.matplotlib.rcParams.update({'font.size': 9})


def connection_to_db(path):
    """
    It opens the connection with the database by parsing the json file in which database credentials are listed
    :param path: path of the database details (i.e. username, password, ...)
    :return: the connection to the database
    """
    with open(path) as data_file:
            json_data = json.load(data_file)

    connection = pymysql.connect(host=json_data['HOST'],
                                 user=json_data['USER'],
                                 password=json_data['PASSWORD'],
                                 db=json_data['DB_NAME'],
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)
    return connection


def fetch_data_from_db(db, company):
    """
    All data contanining the stock price info are retrieved from the database given the stock name
    :param db: connection name
    :param company: company name
    :return: the list of data just fetched
    """
    cur = db.cursor()
    cur.execute("SELECT * FROM Stock_price WHERE company = %s", company)
    query_result = cur.fetchall()

    # list of dates
    result = []

    for i in query_result:
        date_formatted = (str(i['date_stock'])[0:10]).split("-")
        result.append(date_formatted[0]+""+date_formatted[1]+""+date_formatted[2]+","+str(i['close_price'])+","+str(i['volume']))

    return result


def get_angular_coefficient(segment_set, index):
    """
    It returns the angular coefficient of the segment set
    :param: segment expressed as a couple of points with two coordinates x and y
    :return: the angular coefficient
    """

    current_segment = segment_set[index]
    coeff_angular = (current_segment[3]-current_segment[1])/(current_segment[2]-current_segment[0])
    return coeff_angular


def get_constant_term(segment_set, index):
    """
    It returns the constant term of the segment set
    :param: segment expressed as a couple of points with two coordinates x and y
    :return: the angular coefficient
    :return:
    """
    current_segment = segment_set[index]
    coeff_constant_term = (current_segment[2]*current_segment[1]-current_segment[0]*current_segment[3])/\
                          (current_segment[2]-current_segment[0])
    return coeff_constant_term


def evaluate_global_error(data, segment_set):
    """
    :param data: the set of close price data
    :param segment_set: the set of segments
    :return: the global error
    """
    current_segment = []
    total_error = 0

    for i in range(0, len(segment_set)):
        error = 0
        current_angular_coeff = get_angular_coefficient(segment_set, i)
        current_constant_term = get_constant_term(segment_set, i)

        # The equation of the line is y = current_angular_coeff * x + current_constant_term
        for j in range((segment_set[i])[0], (segment_set[i])[2]):
            y = current_angular_coeff * j + current_constant_term
            current_segment.append(y)
            error += abs(y - data[j])

        total_error += error

    return total_error


def draw_window(my_dpi, data, max_error):
    """
    All data contanining the stock price info are retrieved from the database given the stock name
    :param my_dpi: dpi screen
    :param data: data to be plot
    :param max_error: maximum error allowed
    """

    fig = plt.figure(figsize=(1000/my_dpi, 700/my_dpi), dpi=96, facecolor='black')
    fig.suptitle("PIECEWISE SEGMENTATION INTERPOLATION", fontsize="15", color="white", fontweight='bold', bbox={'facecolor': 'red', 'alpha': 0.5, 'pad': 10})

    try:
        stockFile = []
        try:
            for eachLine in data:
                splitLine = eachLine.split(',')
                if len(splitLine) == 3:
                    if 'values' not in eachLine:
                        stockFile.append(eachLine)
        except Exception as e:
            print(str(e), 'failed to organize pulled data.')
    except Exception as e:
        print(str(e), 'failed to pull pricing data')

    try:
        print(stockFile)
        date, closep_raw, volume_raw = np.loadtxt(stockFile, delimiter=',', unpack=True,
                                                              converters={0: mdates.bytespdate2num('%Y%m%d')})
        closep = closep_raw[::-1]

        # First subplot stock price
        ax1 = plt.subplot2grid((3, 2), (0, 0), colspan=3)
        segments = segment.slidingwindowsegment(closep, fit.interpolate, fit.sumsquared_error, max_error)
        draw_plot(closep,plt,ax1,"Sliding window with interpolation")
        draw_segments(segments,'red')
        plt.ylabel('Stock Price')
        plt.title("SLIDING WINDOW - ERROR "+str(evaluate_MSE(closep, segments)), color='Yellow', fontweight='bold')

        # Second subplot
        ax2 = plt.subplot2grid((3, 3), (1, 0), colspan=3)
        segments = segment.topdownsegment(closep, fit.interpolate, fit.sumsquared_error, max_error)
        draw_plot(closep, plt, ax2, "Top down with interpolation")
        draw_segments(segments, 'green')
        plt.ylabel('Stock Price')
        plt.title("TOP DOWN - ERROR "+str(evaluate_MSE(closep, segments)), color='Yellow', fontweight='bold')

        # Third subplot
        ax3 = plt.subplot2grid((3, 3), (2, 0), colspan=3)
        segments = segment.bottomupsegment(closep, fit.interpolate, fit.sumsquared_error, max_error)
        draw_plot(closep, plt, ax3, "Bottom up with interpolation")
        draw_segments(segments,'blue')
        plt.ylabel('Stock Price')
        plt.title("BOTTOM UP - ERROR "+str(evaluate_MSE(closep, segments)), color='Yellow', fontweight='bold')

        plt.subplots_adjust(hspace=0.3)
        plt.show()

    except e:
        print("Error")


def draw_plot(data, plt, ax, plot_title):
    ax.plot(range(len(data)), data, alpha=0.8, color='black')

    ax.grid(True, color='#969696')
    ax.yaxis.label.set_color("w")
    ax.xaxis.label.set_color("w")
    ax.tick_params(axis='y', colors='w')
    ax.tick_params(axis='x', colors='w')
    plt.ylabel('Stock Price')
    plt.title("Sliding window", color='w')
    plt.title(plot_title)
    plt.xlim((0, len(data)-1))


def evaluate_MSE(data, segment_set):
    """
    :param data: the set of close price data
    :param segment_set: the set of segments
    :return: the global error
    """
    total_error = 0

    # Scan through the segments
    for i in range(0, len(segment_set)):
        error = 0
        a = get_angular_coefficient(segment_set, i)
        b = get_constant_term(segment_set, i)

        for j in range((segment_set[i])[0], (segment_set[i])[2]):
            # predicted value
            y = a * j + b
            error += pow((data[j]-y), 2)

        total_error += error/(len(range((segment_set[i])[0], (segment_set[i])[2])))

    return sqrt(total_error)



def draw_segments(segments, color):
    ax = gca()
    for segment in segments:
        line = Line2D((segment[0],segment[2]),(segment[1],segment[3]),color=color)
        ax.add_line(line)


def draw_window_API(my_dpi, max_error, stockToFetch):
    """
    All data contanining the stock price info are retrieved from the database given the stock name
    :param my_dpi: dpi screen
    :param data: data to be plot
    :param max_error: maximum error allowed
    """

    fig = plt.figure(figsize=(1000/my_dpi, 700/my_dpi), dpi=96, edgecolor='k', facecolor='black')
    fig.suptitle("PIECEWISE SEGMENTATION INTERPOLATION", fontsize="15", color="white", fontweight='bold', bbox={'facecolor':'red', 'alpha':0.5, 'pad':10})

    try:
        print('Currently Pulling',stockToFetch)
        urlToVisit = 'http://chartapi.finance.yahoo.com/instrument/1.0/'+stockToFetch+'/chartdata;type=quote;range=5y/csv'
        stockFile =[]
        try:
            sourceCode = urllib.request.urlopen(urlToVisit).read().decode()
            splitSource = sourceCode.split('\n')
            for eachLine in splitSource:
                splitLine = eachLine.split(',')
                if len(splitLine) == 6:
                    if 'values' not in eachLine:
                        stockFile.append(eachLine)
        except Exception as e:
            print(str(e), 'failed to organize pulled data.')
    except Exception as e:
        print(str(e), 'failed to pull pricing data')

    try:
        date, closep, highp, lowp, openp, volume = np.loadtxt(stockFile, delimiter=',', unpack=True,
                                                              converters={0: mdates.bytespdate2num('%Y%m%d')})
        SP = len(date)
        # First subplot
        ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=3)
        segments = segment.slidingwindowsegment(closep, fit.interpolate, fit.sumsquared_error, max_error)
        draw_plot(closep,plt,ax1,"Sliding window with interpolation")
        draw_segments(segments,'red')
        plt.ylabel('Stock Price')
        plt.title("SLIDING WINDOW - ERROR "+str(evaluate_MSE(closep, segments)), color='Yellow', fontweight='bold')


        # Second subplot
        ax2 = plt.subplot2grid((3, 3), (1, 0), colspan=3)
        segments = segment.topdownsegment(closep, fit.interpolate, fit.sumsquared_error, max_error)
        draw_plot(closep, plt, ax2, "Sliding window with interpolation")
        draw_segments(segments,'green')
        plt.ylabel('Stock Price')
        plt.title("TOP DOWN - ERROR "+str(evaluate_MSE(closep, segments)), color='Yellow', fontweight='bold')

        # Third subplot
        ax3 = plt.subplot2grid((3, 3), (2, 0), colspan=3)
        segments = segment.bottomupsegment(closep, fit.interpolate, fit.sumsquared_error, max_error)
        draw_plot(closep, plt, ax3, "Sliding window with interpolation")
        draw_segments(segments,'blue')
        plt.ylabel('Stock Price')
        plt.title("BOTTOM UP - ERROR "+str(evaluate_MSE(closep, segments)), color='Yellow', fontweight='bold')

        plt.subplots_adjust(hspace=0.3)
        plt.show()

    except e:
        print("Error")

if __name__ == '__main__':

    """
    CONSTANTS
    """
    MY_DPI = 96
    PATH_AWS_DB = 'resources/AWS_DB_details.json'

    # Connection to the database
    connection = connection_to_db(PATH_AWS_DB)

    # Data is fetched from db
    stock = input("Stock name: ")
    err = input("Max error: ")
    res = fetch_data_from_db(connection, stock)

    # Figure is built
    draw_window(MY_DPI, res, float(err))
    # draw_window_API(MY_DPI, float(err), stock)



