import xlsxwriter
import json
import datetime
import itertools
from random import *
import time
import pickle
import calendar


def read_data(filename):
    # load binary file
    f = open(filename, "rb")
    data = pickle.load(f)
    f.close()
    return data


def timestamps_to_datetimes(data):
    # Convert timestamps in datetimes objects
    timestamps=list(data.keys())
    datetime_objects = [datetime.datetime.fromtimestamp(timestamp) for timestamp in timestamps]
    return datetime_objects


def split_datetimes_by_year(datetime_objects):
    # Separate datetimes objects by year
    return [list(g) for k, g in itertools.groupby(datetime_objects, key=lambda d: d.year)]

def split_datetimes_by_month(datetime_objects):
    # Separate datetimes objects by month
    return [list(g) for k, g in itertools.groupby(datetime_objects, key=lambda d: d.month)]

def split_datetimes_by_day(datetime_objects):
    # Separate datetimes objects by day
    return [list(g) for k, g in itertools.groupby(datetime_objects, key=lambda d: d.day)]

def split_datetimes_by_hour(datetime_objects):
    # Separate datetimes objects by hour
    return [list(g) for k, g in itertools.groupby(datetime_objects, key=lambda d: d.hour)]


def prepare_for_monthly_chart(data, key=["M","NM"]):
    # Split data by month
    months_names=['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    datetime_objects = timestamps_to_datetimes(data)
    dt_by_month = split_datetimes_by_month(datetime_objects)
    masked=[]
    not_masked=[]
    months=[]
    for month in dt_by_month:

        months.append(datetime.datetime(month[0].year,month[0].month,1))
        m_samples=[]
        nm_samples=[]
        for sample in month:

            timestamp = sample.timestamp()
            m_samples=m_samples+data[timestamp][key[0]]
            nm_samples=nm_samples+data[timestamp][key[1]]
        masked.append(len(set(m_samples)))
        not_masked.append(len(set(nm_samples)))

    return [months, masked, not_masked]

def prepare_for_daily_chart(data, key=["M","NM"]):
    # Split data by day
    datetime_objects = timestamps_to_datetimes(data)
    dt_by_day = split_datetimes_by_day(datetime_objects)
    masked=[]
    not_masked=[]
    days=[]
    for day in dt_by_day:
        days.append(datetime.datetime(day[0].year,day[0].month,day[0].day))
        m_samples=[]
        nm_samples=[]
        for sample in day:
            timestamp = sample.timestamp()
            m_samples=m_samples+data[timestamp][key[0]]
            nm_samples=nm_samples+data[timestamp][key[1]]
        masked.append(len(set(m_samples)))
        not_masked.append(len(set(nm_samples)))
    return [days, masked, not_masked]



def prepare_for_hourly_last_week_chart(data, key=["M","NM"]):
    # Take the data of the last week if available and split it by hour  
    datetime_objects = timestamps_to_datetimes(data)

    dt_by_days = split_datetimes_by_day(datetime_objects)
    
    today = dt_by_days[-1]
    today_masked=[]
    today_not_masked=[]
    today_hours=[]

    today_by_hour = split_datetimes_by_hour(today)
    for h in today_by_hour:
        today_hours.append(datetime.datetime(h[0].year,h[0].month,h[0].day,h[0].hour))
        m_samples=[]
        nm_samples=[]
        for sample in h:
            timestamp = sample.timestamp()
            m_samples=m_samples+data[timestamp][key[0]]
            nm_samples=nm_samples+data[timestamp][key[1]]
        today_masked.append(len(set(m_samples)))
        today_not_masked.append(len(set(nm_samples)))
    if len(dt_by_days)>7:
        week_days = dt_by_days[-8:-1]           
        week_masked=[]
        week_not_masked=[]
        week_hours=[]
        for day in week_days:
            week_by_hour = split_datetimes_by_hour(day)
            week_masked.append([])
            week_not_masked.append([])
            week_hours.append([])
            for h in week_by_hour:
                week_hours[-1].append(datetime.datetime(h[0].year,h[0].month,h[0].day,h[0].hour))
                m_samples=[]
                nm_samples=[]
                for sample in h:
                    timestamp = sample.timestamp()
                    m_samples=m_samples+data[timestamp][key[0]]
                    nm_samples=nm_samples+data[timestamp][key[1]]
                week_masked[-1].append(len(set(m_samples)))
                week_not_masked[-1].append(len(set(nm_samples)))
    else:
        week_hours=[]
        week_masked=[]
        week_not_masked=[]

    return [[today_hours, today_masked, today_not_masked],[week_hours, week_masked, week_not_masked]]
    
    
       

def hourly_last_week_chart(preprocessed_data, workbook,sheetname="hourly_presence",kind='column', dim=[800,600]):
    # Function to draw hourly charts on excel

    headings = ['Days','With Mask', 'Without Mask']

    # add sheet to workbook
    worksheet = workbook.add_worksheet(sheetname)

    chart=[]
    bold = workbook.add_format({'bold': 1})
    dy=5
    dx=0



    today_data=preprocessed_data[0]

    week_data=preprocessed_data[1]

    # get data for the current day
    data = today_data

    X=[d.strftime("%H") for d in data[0]]

    # add a chart
    chart.append(workbook.add_chart({'type': kind}))

    # add data to worksheet
    headings = ['Days','With Mask', 'Without Mask']
    gap=1000

    worksheet.write_row('B'+str(dy-1), [data[0][0].strftime("%a %d %b %Y")], bold)
    worksheet.write_row(chr(ord('A')+dx)+str(gap), headings, bold)
    worksheet.write_column(chr(ord('A')+dx)+str(gap+1), X)
    worksheet.write_column(chr(ord('B')+dx)+str(gap+1), data[1])
    worksheet.write_column(chr(ord('C')+dx)+str(gap+1), data[2])

    # Configure the chart
    chart[0].add_series({'name': '='+sheetname+'!$'+chr(ord('B')+dx)+'$'+str(gap),'categories': '='+sheetname+'!$'+chr(ord('A')+dx)+'$'+str(gap+1)+':$'+chr(ord('A')+dx)+'$'+str(len(data[0])+2+gap),'values': '='+sheetname+'!$'+chr(ord('B')+dx)+'$'+str(gap+1)+':$'+chr(ord('B')+dx)+'$'+str(len(data[0])+2+gap)})
    chart[0].add_series({'name': '='+sheetname+'!$'+chr(ord('C')+dx)+'$'+str(gap),'categories': '='+sheetname+'!$'+chr(ord('A')+dx)+'$'+str(gap+1)+':$'+chr(ord('A')+dx)+'$'+str(len(data[1])+2+gap),'values': '='+sheetname+'!$'+chr(ord('C')+dx)+'$'+str(gap+1)+':$'+chr(ord('C')+dx)+'$'+str(len(data[0])+2+gap)})

    # set chart size
    chart[0].set_size({'width': dim[0], 'height': dim[1]})
    
    # Insert the chart into the worksheet.
    worksheet.insert_chart('B'+str(dy), chart[0])

    dx+=3
    dy+=dim[1]/15

    n_days=len(week_data[0])
    for i in range(len(week_data[0])):

        

        # get data for the current day
        data=[]
        data.append(week_data[0][n_days-1-i])
        data.append(week_data[1][n_days-1-i])
        data.append(week_data[2][n_days-1-i])
        
        
        X=[d.strftime("%H") for d in data[0]]

        # add a chart
        chart.append(workbook.add_chart({'type': kind}))

        # add data to worksheet
        headings = ['Days','With Mask', 'Without Mask']
        gap=1000

        worksheet.write_row('B'+str(dy-1), [data[0][0].strftime("%a %d %b %Y")], bold)
        worksheet.write_row(chr(ord('A')+dx)+str(gap), headings, bold)
        worksheet.write_column(chr(ord('A')+dx)+str(gap+1), X)
        worksheet.write_column(chr(ord('B')+dx)+str(gap+1), data[1])
        worksheet.write_column(chr(ord('C')+dx)+str(gap+1), data[2])

        # Configure the chart
        chart[i+1].add_series({'name': '='+sheetname+'!$'+chr(ord('B')+dx)+'$'+str(gap),'categories': '='+sheetname+'!$'+chr(ord('A')+dx)+'$'+str(gap+1)+':$'+chr(ord('A')+dx)+'$'+str(len(data[0])+2+gap),'values': '='+sheetname+'!$'+chr(ord('B')+dx)+'$'+str(gap+1)+':$'+chr(ord('B')+dx)+'$'+str(len(data[0])+2+gap)})
        chart[i+1].add_series({'name': '='+sheetname+'!$'+chr(ord('C')+dx)+'$'+str(gap),'categories': '='+sheetname+'!$'+chr(ord('A')+dx)+'$'+str(gap+1)+':$'+chr(ord('A')+dx)+'$'+str(len(data[1])+2+gap),'values': '='+sheetname+'!$'+chr(ord('C')+dx)+'$'+str(gap+1)+':$'+chr(ord('C')+dx)+'$'+str(len(data[0])+2+gap)})

        # set chart size
        chart[i+1].set_size({'width': dim[0], 'height': dim[1]})
        
        # Insert the chart into the worksheet.
        worksheet.insert_chart('B'+str(dy), chart[i+1])

        dx+=3
        dy+=dim[1]/15
    
    return workbook

def export_records(outputfile, data):
    # Function to draw charts on excel
    
    workbook = xlsxwriter.Workbook(outputfile)
    
    monthly_data=prepare_for_monthly_chart(data)
    daily_data=prepare_for_daily_chart(data)
    hourly_data=prepare_for_hourly_last_week_chart(data)

    workbook=hourly_last_week_chart(hourly_data, workbook)

    ndays=len(daily_data[0])
    if ndays>7:
        workbook=create_chart(workbook, daily_data, "Daily_report","Days",'line')  
    elif ndays<=7 and ndays>0:
        workbook=create_chart(workbook, daily_data, "Daily_report","Days",'column')

    nmonths=len(monthly_data[0])
    if nmonths>12:
        workbook=create_chart(workbook, monthly_data, "Monthly_report","Months",'line') 
    elif nmonths<=12 and nmonths>0:
        workbook=create_chart(workbook,monthly_data, "Monthly_report","Months",'column')

    workbook.close()



def create_chart(workbook, data, sheetname,text,kind,dim=[640,480]):

  
    
    worksheet = workbook.add_worksheet(sheetname)

    # Create a new Chart object.
    chart = workbook.add_chart({'type': kind})

    X=[d.strftime("%b %Y") for d in data[0]]

    bold = workbook.add_format({'bold': 1})

    # Add the worksheet data that the charts will refer to.
    headings = [text,'With Mask', 'Without Mask']

    gap=1000
    worksheet.write_row('B2', [sheetname], bold)
    worksheet.write_row('A'+str(gap), headings, bold)

    worksheet.write_column('A'+str(gap+1), X)
    worksheet.write_column('B'+str(gap+1), data[1])
    worksheet.write_column('C'+str(gap+1), data[2])

    # Configure the chart. In simplest case we add one or more data series.
    chart.add_series({'name': '='+sheetname+'!$B$'+str(gap),'categories': '='+sheetname+'!$A$'+str(gap+1)+':$A$'+str(len(data[0])+2+gap),'values': '='+sheetname+'!$B$'+str(gap+1)+':$B$'+str(len(data[0])+2+gap)})
    chart.add_series({'name': '='+sheetname+'!$C$'+str(gap),'categories': '='+sheetname+'!$A$'+str(gap+1)+':$A$'+str(len(data[1])+2+gap),'values': '='+sheetname+'!$C$'+str(gap+1)+':$C$'+str(len(data[0])+2+gap)})

    chart.set_size({'width': dim[0], 'height': dim[1]})

    # Insert the chart into the worksheet.
    worksheet.insert_chart('B4', chart)


    # Create a new Chart object.
    chart2 = workbook.add_chart({'type': kind})


    bold = workbook.add_format({'bold': 1})

    # Add the worksheet data that the charts will refer to.
    headings = [text,'Percentage of people with mask']

 
    worksheet.write_row('B40', ["Percentage of people with mask"], bold)
    worksheet.write_row('D'+str(gap), headings, bold)

    perc=[data[1][i]/(data[1][i]+data[2][i])*100 if (data[2][i]!=0 or data[1][i]!=0) else 0 for i in range(len(data[1]))]
    worksheet.write_column('D'+str(gap+1), X)
    worksheet.write_column('E'+str(gap+1), perc)

    # Configure the chart. In simplest case we add one or more data series.
    chart2.add_series({'name': '='+sheetname+'!$E$'+str(gap),'categories': '='+sheetname+'!$D$'+str(gap+1)+':$D$'+str(len(data[0])+2+gap),'values': '='+sheetname+'!$E$'+str(gap+1)+':$E$'+str(len(data[0])+2+gap)})
    
    chart2.set_size({'width': dim[0], 'height': dim[1]})

    # Insert the chart into the worksheet.
    worksheet.insert_chart('B42', chart2)
    
    return workbook
