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
    priority = poobrains.storage.fields.IntegerField(null=True, choices=[
                                                                            (None, 'None'),
                                                                            (-2, 'Very low'),
                                                                            (-1, 'Low'),
                                                                            (0, 'Normal'),
                                                                            (1, 'High'),
                                                                            (2, 'VERY HIGH')
                                                                        ])
    deadline = poobrains.storage.fields.DateTimeField(default=tomorrow, null=True)
    description = poobrains.md.MarkdownField()


class RecurringTask(poobrains.commenting.Commentable):

    created = poobrains.storage.fields.DateTimeField(default=datetime.datetime.now)
    title = poobrains.storage.fields.CharField()
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
    day_month = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(1,32)])
    day_week = poobrains.storage.fields.IntegerField(null=True, choices=[
        (None, 'Any'),
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday')
    ])
    hour = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(0,24)])
    minute = poobrains.storage.fields.IntegerField(null=True, choices=[(None, 'Any')] + [(x, x) for x in range(0,60)])
    description = poobrains.md.MarkdownField()
    latest_task = poobrains.storage.fields.ForeignKeyField(Task, null=True)


    @classmethod
    def get_new_tasks(cls):

        """ THIS IS BULLSHIT? """

        now = datetime.datetime.now()
        return cls.select().where(
            cls.latest_task.is_null() |

            (

                (cls.year.is_null(False) & cls.year <= now.year ) &
                (cls.month.is_null(False) | cls.month <= now.month) &
                (cls.day_month.is_null(False) | cls.day_month <= now.day) &
                (cls.day_week.is_null(False) | cls.day_week <= now.isoweekday()) &
                (cls.hour.is_null(False) | cls.hour <= now.hour) &
                (cls.minute.is_null(False) | cls.minute <= now.minute)
            )
        )

@app.cron
def create_recurring():

    now = datetime.datetime.now()
    dated_tasks = collections.OrderedDict()

    for template in RecurringTask.select():

        base_date = tpl.latest_task.created if tpl.latest_task is None else tpl.created

        year_changed = now.year > base_date.year
        month_changed = year_changed or now.month > base_date.month
        week_changed = month_changed or now.isocalendar()[1] > base_date.isocalendar()[1]
        day_changed = week_changed or month_changed or now.day > base_date.day
        hour_changed = day_changed or now.hour > base_date.hour
        minute_changed = hour_changed or now.minute > base_date.minute

        #below_year_changed = month_changed or week_changed or day_changed or hour_changed or minute_changed
        #below_month_changed = week_changed or day_changed or hour_changed or minute_changed

        years = []
        for year in range(base_date.year, now.year + 1):
            if not template.year or template.year == year:
                years.append(year)

        months = collections.OrderedDict()
        for year in years:

            months[year] = []
            # Determine whether this is the first, last (or neither) year of the range
            first_year = year == years[0]
            last_year = year == years[-1]

            if template.month:
                months.[year]append('%d-%d' % year, template.month)


if __name__ == '__main__':
    app.cli()
