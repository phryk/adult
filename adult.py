#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" How do I even adult? """

import math
import collections
import datetime
import calendar
import click
import poobrains

app = poobrains.app

def tomorrow():

    return datetime.datetime.now() + datetime.timedelta(days=1)


class TaskForm(poobrains.form.AddForm):

    def __init__(self, model_or_instance, **kwargs):

        super(TaskForm, self).__init__(model_or_instance, **kwargs)
        self.dependencies = poobrains.form.fields.MultiChoice(type=poobrains.form.types.StorableInstanceParamType(Task))


class Task(poobrains.commenting.Commentable):

    class Meta:
        order_by = ('-created', '-priority', 'checkdate')

    form_add = TaskForm

    created = poobrains.storage.fields.DateTimeField(default=datetime.datetime.now)
    title = poobrains.storage.fields.CharField()
    checkdate = poobrains.storage.fields.DateTimeField(default=tomorrow, null=True)
    priority = poobrains.storage.fields.IntegerField(null=True, form_widget=poobrains.form.fields.Select, choices=[
        (None, 'None'),
        (-2, 'Very low'),
        (-1, 'Low'),
        (0, 'Normal'),
        (1, 'High'),
        (2, 'VERY HIGH')
    ])
    status = poobrains.storage.fields.CharField(default='new', form_widget=poobrains.form.fields.Select, choices=[
        ('new', 'new'),
        ('ongoing', 'ongoing'),
        ('finished', 'finished'),
        ('aborted', 'aborted')
    ])
    progress = poobrains.storage.fields.IntegerField(default=0, constraints=[
        poobrains.storage.fields.Check('progress >= 0'),
        poobrains.storage.fields.Check('progress <= 100')
    ])
    description = poobrains.md.MarkdownField()


class RecurringTask(poobrains.commenting.Commentable):

    created = poobrains.storage.fields.DateTimeField(default=datetime.datetime.now)
    title = poobrains.storage.fields.CharField()
    checkdate = poobrains.storage.fields.IntegerField(null=True, help_text='Time frame in seconds')
    priority = poobrains.storage.fields.IntegerField(null=True, form_widget=poobrains.form.fields.Select, choices=[
        (None, 'None'),
        (-2, 'Very low'),
        (-1, 'Low'),
        (0, 'Normal'),
        (1, 'High'),
        (2, 'VERY HIGH')
    ])
    year = poobrains.storage.fields.IntegerField(null=True)
    month = poobrains.storage.fields.IntegerField(null=True, form_widget=poobrains.form.fields.Select, choices=[
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
    weekday_month = poobrains.storage.fields.IntegerField(null=True, form_widget=poobrains.form.fields.Select, choices=[(None, 'Any')] + [(x, x) for x in range(1,7)])
    weekday = poobrains.storage.fields.IntegerField(null=True, form_widget=poobrains.form.fields.Select, choices=[
        (None, 'Any'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday')
    ])
    day = poobrains.storage.fields.IntegerField(null=True, form_widget=poobrains.form.fields.Select, choices=[(None, 'Any')] + [(x, x) for x in range(1,32)])
    hour = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(0,24)], help_text='0-23')
    minute = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(0,60)], help_text='0-59')
    description = poobrains.md.MarkdownField()
    latest_task = poobrains.storage.fields.ForeignKeyField(Task, null=True)


class TaskDependency(poobrains.storage.Model):

    task = poobrains.storage.fields.ForeignKeyField(Task, related_name='dependencies')
    dependency = poobrains.storage.fields.ForeignKeyField(Task, related_name='provides', constraints=[poobrains.storage.fields.Check('dependency_id <> task_id')])


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

        try:

            if template.latest_task:
                base_date = template.latest_task.created
            else: # for some reason this can be None without triggering Task.DoesNotExist
                base_date = template.created

        except Task.DoesNotExist:
            base_date = template.created


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

            if not template.month is None:

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

                if not template.day is None:

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

                    else:
                        days = range(1, 32) # days that don't exist are weeded out by trying to create a datetime from it

                    for day in days:
                   
                        try:
                            dt = datetime.datetime(year=year, month=month, day=day)
                        except ValueError:
                            continue # means we have an invalid date on our hands, skip to next iteration of the loop

                        weekday_valid = not template.weekday or dt.isoweekday() == template.weekday
                        weekday_month_valid = not template.weekday_month or math.ceil(day / 7) == template.weekday_month

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

                    if not template.hour is None:

                        if first_day and last_day:
                            valid = template.hour >= base_date.hour and template.hour <= now.hour
                        elif first_day:
                            valid = template.hour >= base_date.hour
                        elif last_day:
                            valid = template.hour <= now.hour
                        else:
                            valid = True

                        if valid:
                            dates[year][month][day][template.hour] = collections.OrderedDict()

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

                        if not template.minute is None:

                            if first_hour and last_hour:
                                valid = template.minute > base_date.minute and template.minute <= now.minute
                            elif first_hour:
                                valid = template.minute > base_date.minute
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
                            elif first_hour:
                                for minute in range(base_date.minute + 1, 60):
                                    task_dates.append(datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute))
                            elif last_hour:
                                for minute in range(0, now.minute + 1):
                                    task_dates.append(datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute))
                            else:
                                for minute in range(0, 60):
                                    task_dates.append(datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute))


        click.echo("Creating %d tasks for '%s'." % (len(task_dates), template.title))
        with click.progressbar(task_dates) as proxy:

            for date in proxy:

                task = Task()
                task.name = "%s-%d-%d-%d-%d-%d" % (template.name, date.year, date.month, date.day, date.hour, date.minute)
                task.owner = template.owner
                task.group = template.group
                task.status = 'new'
                task.title = template.title
                task.created = date
                if template.checkdate:
                    task.checkdate = date + datetime.timedelta(seconds=template.checkdate)
                task.priority = template.priority
                task.description = template.description

                task.save(force_insert=True)

        if len(task_dates):
            template.latest_task = task
            template.save()

if __name__ == '__main__':
    app.cli()
