#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" How do I even adult? """

import datetime
import collections
import poobrains

app = poobrains.app

def tomorrow():

    return datetime.datetime.now() + datetime.timedelta(days=1)


class Task(poobrains.commenting.Commentable):

    created = poobrains.storage.fields.DateTimeField(default=datetime.datetime.now)
    title = poobrains.storage.fields.CharField()
    checkdate = poobrains.storage.fields.DateTimeField(default=tomorrow, null=True)
    priority = poobrains.storage.fields.IntegerField(null=True, choices=[
        (None, 'None'),
        (-2, 'Very low'),
        (-1, 'Low'),
        (0, 'Normal'),
        (1, 'High'),
        (2, 'VERY HIGH')
    ])
    description = poobrains.md.MarkdownField()


class RecurringTask(poobrains.commenting.Commentable):

    created = poobrains.storage.fields.DateTimeField(default=datetime.datetime.now)
    title = poobrains.storage.fields.CharField()
    checkdate = poobrains.storage.fields.IntegerField(null=True, help_text='Time frame in seconds')
    priority = poobrains.storage.fields.IntegerField(null=True, choices=[
        (None, 'None'),
        (-2, 'Very low'),
        (-1, 'Low'),
        (0, 'Normal'),
        (1, 'High'),
        (2, 'VERY HIGH')
    ])
    year = poobrains.storage.fields.IntegerField(null=True)
    month = poobrains.storage.fields.IntegerField(null=True, choices=[
        (None, 'Any'),
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June'),
        (7, 'July'),
        (8, 'August'),
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December')
    ])
    #TODO: week of month (1-6?)
    weekday_month = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(1,7)])
    weekday = poobrains.storage.fields.IntegerField(null=True, choices=[
        (None, 'Any'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday')
    ])
    day = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(1,32)])
    hour = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(0,24)])
    minute = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(0,60)])
    description = poobrains.md.MarkdownField()
    latest_task = poobrains.storage.fields.ForeignKeyField(Task, null=True)


#    @classmethod
#    def get_new_tasks(cls):
#
#        """ THIS IS BULLSHIT? """
#
#        now = datetime.datetime.now()
#        return cls.select().where(
#            cls.latest_task.is_null() |
#
#            (
#
#                (cls.year.is_null(False) & cls.year <= now.year ) &
#                (cls.month.is_null(False) | cls.month <= now.month) &
#                (cls.day.is_null(False) | cls.day <= now.day) &
#                (cls.weekday.is_null(False) | cls.weekday <= now.isoweekday()) &
#                (cls.hour.is_null(False) | cls.hour <= now.hour) &
#                (cls.minute.is_null(False) | cls.minute <= now.minute)
#            )
#        )


class Reward(poobrains.commenting.Commentable):

    title = poobrains.storage.fields.CharField()
    description = poobrains.md.MarkdownField(null=True)

@app.cron
def create_recurring():

    if app.config['DEBUG']:
        app.debugger.set_trace()

    now = datetime.datetime.now()
    dated_tasks = collections.OrderedDict()

    for template in RecurringTask.select():

        base_date = tpl.latest_task.created if tpl.latest_task is None else tpl.created

        #year_changed = now.year > base_date.year
        #month_changed = year_changed or now.month > base_date.month
        #week_changed = month_changed or now.isocalendar()[1] > base_date.isocalendar()[1]
        #day_changed = week_changed or month_changed or now.day > base_date.day
        #hour_changed = day_changed or now.hour > base_date.hour
        #minute_changed = hour_changed or now.minute > base_date.minute

        #below_year_changed = month_changed or week_changed or day_changed or hour_changed or minute_changed
        #below_month_changed = week_changed or day_changed or hour_changed or minute_changed

        dates = collections.OrderedDict()

        # add years
        for year in range(base_date.year, now.year + 1):
            if not template.year or template.year == year:
                dates[year] = collections.OrderedDict()

        # add months
        for year, _ in dates.iteritems():

            # Determine whether this is the first, last (or neither) year of the range
            first_year = year == dates.keys()[0]
            last_year = year == dates.keys()[-1]

            if template.month:

                if first_year and last_year:
                    valid = template.month >= base_date.month and template.month <= now.month
                elif first_year:
                    valid = template.month >= base_date.month
                elif last_year:
                    valid = template.month <= now.month
                else:
                    valid = True

                if valid:
                    dates[year][template.month] = collections.OrderedDict()


            else:

                if first_year and last_year:
                    months = range(base_date.month, now.month + 1)

                elif first_year:
                    months = range(base_date.month, 13)

                elif last_year:
                    months = range(1, now.month + 1)

                else:
                    months = range(1, 13)

                for month in months:
                    dates[year][month] = collections.OrderedDict()


        # add days
        for year, months in dates.iteritems():

            first_year = year == dates.keys()[0]
            last_year = year == dates.keys()[-1]

            for month, _ in months.iteritems():

                first_month = first_year and month == base_date.month
                last_month = last_year and month == now.month 

                if template.day:

                    #first_year_valid = first_year and month <= base_date.month
                    #middle_year_valid = not first_year and not last_year
                    #last_year_valid = last_year and month >= now.month
                    #weekday_valid = not template.weekday or datetime.datetime(year, month, template.day).isoweekday == template.weekday - 1

                    if first_month and last_month:
                        valid = template.day >= base_date.day and template.day <= now.day
                    elif first_month:
                        valid = template.day >= base_date.day
                    elif last_month:
                        valid = template.day <= now.day
                    else:
                        valid = True
                    
                    valid = valid and (not template.weekday or datetime.datetime(year, month, template.day).isoweekday() == template.weekday) # check if the date has the correct weekday
                
                    #if (first_year_valid or middle_year_valid or last_year_valid) and weekday_valid:
                    if valid:
                        dates[year][month][template.day] = collections.OrderedDict()

                else:

                    if first_month and last_month:
                        days = range(base_date.day, now.day + 1)

                    elif first_month:
                        days = range(base_date.day, calendar.monthrange(year, month)[1] + 1)

                    elif last_month:
                        days = range(1, now.day + 1)

                    for day in days:
                    
                        dt = datetime.datetime(year=year, month=month, day=day)

                        weekday_valid = not template.weekday or dt.isoweekday() == template.weekday
                        weekday_month_valid = not template.weekday_month or ceil(day / 7) == template.weekday_month

                        if weekday_valid and weekday_month_valid: 
                            dates[year][month][day] = collections.OrderedDict()


        # add hours
        for year, months in dates.iteritems():

            first_year = year == dates.keys()[0]
            last_year = year == dates.keys()[-1]

            for month, days in months.iteritems():

                first_month = first_year and month == base_date.month
                last_month = last_year and month == now.month

                for day, _ in days.iteritems():

                    first_day = first_month and day == base_date.day
                    last_day = last_month and day == now.day 

                    if template.hour:

                        if first_day and last_day:
                            valid = template.hour >= base_date.hour and template.hour <= now.hour
                        elif first_day:
                            valid = template.hour >= base_date.hour
                        elif last_day:
                            valid = template.hour <= now.hour
                        else:
                            valid = True

                        if valid:
                            dates[year][month][day][hour] = collections.OrderedDict()

                    else:

                        if first_day and last_day:
                            hours = range(base_date.hour, now.hour + 1)
                        elif first_day:
                            hours = range(base_date.hour, 24)
                        elif last_day:
                            hours = range(0, now.hour + 1)
                        else:
                            hours = range(0,24)

                        for hour in hours:
                            dates[year][month][day][hour] = collections.OrderedDict()


        task_dates = []

        # add minutes
        for year, months in dates.iteritems():

            first_year = year == dates.keys()[0]
            last_year = year == dates.keys()[-1]

            for month, days in months.iteritems():

                first_month = first_year and month == base_date.month
                last_month = last_year and month == now.month

                for day, hours in days.iteritems():

                    first_day = first_month and day == base_date.day
                    last_day = last_month and day == now.day 

                    for hour, _ in hours.iteritems():

                        first_hour = first_day and hour == base_date.hour
                        last_hour = last_day and hour == now.hour

                        if template.minute:

                            if first_hour and last_hour:
                                valid = template.minute >= base_date.minute and template.minute <= now.minute
                            elif first_hour:
                                valid = template.minute >= base_date.minute
                            elif last_hour:
                                valid = template.minute <= now.minute
                            else:
                                valid = True

                            if valid:
                                task_dates.append(datetime.datetime(year=year, month=month, day=day, hour=hour, minute=template.minute))

                        else:

                            if first_hour and last_hour:
                                for minute in range(base_date.minute + 1, now.minute + 1):
                                    task_dates.append(datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute))


        click.echo("Creating %d tasks for '%s'." % (len(task_dates), template.title))
        with click.progressbar(task_dates) as proxy:

            for date in proxy:

                task = Task()
                task.title = template.title
                task.created = date
                task.checkdate = date + datetime.timedelta(seconds=template.checkdate)
                task.priority = template.priority
                task.description = template.description

                task.save(force_insert=True)

        template.latest = task
        template.save()

if __name__ == '__main__':
    app.cli()
