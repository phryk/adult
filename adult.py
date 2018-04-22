#!/usr/bin/env python2
# -*- coding: utf-8 -*-

""" How do I even adult? """

import math
import collections
import datetime
import calendar
import click
import flask
import poobrains

app = poobrains.app

def tomorrow():

    return datetime.datetime.now() + datetime.timedelta(days=1)


def firstweekday(weekday, first_day_of_month):

    """ return day of month which is first occurence of weekday in a month beginning on weekday first_day_of_month. """

    weekday = weekday - 1
    first_day_of_month = first_day_of_month - 1

    if first_day_of_month <= weekday:
        return weekday - first_day_of_month + 1
    elif first_day_of_month > weekday:
        return weekday - first_day_of_month + 7 + 1


class TaskForm(poobrains.form.AddForm):

    def __init__(self, model_or_instance, **kwargs):

        super(TaskForm, self).__init__(model_or_instance, **kwargs)
        choices = []
        for task in Task.list('read', flask.g.user):
            choices.append((task, task.title))
        dep_value = [x.dependency for x in self.instance.task_dependencies]
        self.dependencies = poobrains.form.fields.Select(type=poobrains.form.types.StorableInstanceParamType(Task), multi=True, choices=choices, value=dep_value)


    def process(self, submit):

        r = super(TaskForm, self).process(submit)

        if submit == 'submit':

            dependencies = self.fields['dependencies'].value

            TaskDependency.delete().where(TaskDependency.task == self.instance).execute()

            try:
                for dependency in dependencies:
                    newdep = TaskDependency()
                    newdep.task = self.instance
                    newdep.dependency = dependency
                    newdep.save(force_insert=True)

            except poobrains.storage.IntegrityError:
                poobrains.flash("At least have the decency to build an indirect loop!")

        return r


@app.expose('/task', force_secure=True)
class Task(poobrains.commenting.Commentable):

    class Meta:
        order_by = ('checkdate', '-priority', '-date')

    form_add = TaskForm
    form_edit = TaskForm

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
    reward_served = poobrains.storage.fields.BooleanField(default=False)


    @property
    def css_class(self):

        classes = []
        classes.append(self.checkdate_css)
        classes.append(self.priority_css)


        return ' '.join(classes)


    @property
    def checkdate_css(self):
        if isinstance(self.checkdate, datetime.datetime):

            now = datetime.datetime.now()

            if self.checkdate < now:
                return 'checkdate-passed'

            elif self.checkdate - datetime.timedelta(days=1) < now: # checkdate within the next 24h
                return 'checkdate-24h'

            return ''


    @property
    def priority_label(self):

        """ gives the choice of the currently set priority """

        return dict(self.__class__.priority.choices)[self.priority]


    @property
    def priority_css(self):
        return 'priority-%s' % self.priority_label.lower().replace(' ', '-')


    @property
    def progress_svg(self):
        return Progress(handle=self.progress).render('raw')


    def validate(self):
        pass # FIXME/TODO: dependency resolution

    def save(self, **kwargs):

        if self._pk and not self.reward_served and self.status == 'finished': # FIXME: _pk is an ugly hack to determin if we're editing or adding but peewee didn't offer anything better last i checked

            reward_token = RewardToken()
            reward_token.task = self
            reward_token.owner = self.owner
            reward_token.group = self.group
            reward_token.save(force_insert=True)

            self.reward_served = True

        return super(Task, self).save(**kwargs)

    @classmethod
    def class_tree(cls, root=None, current_depth=0):
       
        if current_depth == 0:
            tree = poobrains.rendering.Tree(root=poobrains.rendering.RenderString('dependencies'), mode='inline')
        else:
            tree = poobrains.rendering.Tree(root=root, mode='inline')

        if current_depth > 100:

            if root:
                message = "Possible loop in dependencies of Task:'%s'."  % root.name
            else:
                message = "Possible loop in dependencies of a Task but don't have a root for this tree. Are you fucking with current_depth manually?"

            app.logger.error(message)
            return tree 

        deps = TaskDependency.select().where(TaskDependency.task == root)

        for dep in deps:
            tree.children.append(dep.dependency.tree(current_depth=current_depth+1))

        return tree


    def tree(self, current_depth=0):

        return self.__class__.class_tree(root=self, current_depth=current_depth)


class RecurringTask(poobrains.commenting.Commentable):

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
    weeks = poobrains.storage.fields.IntegerField(null=True, help_text="Every n weeks after creation.")
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

    class Meta:
        order_by = ['task']
        primary_key = poobrains.storage.CompositeKey('task', 'dependency')

    task = poobrains.storage.fields.ForeignKeyField(Task, related_name='task_dependencies')
    dependency = poobrains.storage.fields.ForeignKeyField(Task, related_name='provides', constraints=[poobrains.storage.fields.Check('dependency_id <> task_id')])


@app.expose('/rewards/', mode='full')
class Reward(poobrains.commenting.Commentable):

    title = poobrains.storage.fields.CharField()
    description = poobrains.md.MarkdownField(null=True)


class RedeemForm(poobrains.auth.BoundForm):

    title = "Redeem a token"

    def __init__(self, *args, **kwargs):
        
        super(RedeemForm, self).__init__(*args, **kwargs)

        choices = []
        for choice in self.instance.reward_choices:
            choices.append((choice.reward, choice.reward.render('inline')))

        self.reward = poobrains.form.fields.Radio(choices=choices, type=poobrains.form.types.StorableInstanceParamType(Reward))
        self.submit = poobrains.form.Button(type='submit', label=u'🍰')


    def process(self, *args, **kwargs):

        reward = self.fields['reward'].value

        if reward:

            self.instance.reward = reward
            self.instance.redeemed = True
            self.instance.save()

            poobrains.flash("Token redeemed, enjoy your reward now! :)")
            return poobrains.redirect(reward.url('full'))

        flash(u"The cake might be a lie. 🤔", 'error')
        return self


@app.expose('/tokens/', mode='redeem')
class RewardToken(poobrains.auth.Administerable):

    task = poobrains.storage.fields.ForeignKeyField(Task)
    reward = poobrains.storage.fields.ForeignKeyField(Reward, null=True)
    redeemed = poobrains.storage.fields.BooleanField(default=False)

    form_redeem = RedeemForm # tells self.form to use RedeemForm for mode 'redeem' updates

    class Meta:

        modes = collections.OrderedDict([
            ('add', 'create'),
            ('teaser', 'read'),
            ('inline', 'read'),
            ('full', 'read'),
            ('edit', 'update'),
            ('delete', 'delete'),
            ('redeem', 'update')
        ])


    def save(self, **kwargs):

        rv = super(RewardToken, self).save(**kwargs)

        if not len(self.reward_choices):

            for reward in Reward.select().order_by(poobrains.storage.fn.Random()).limit(5):

                choice = RewardTokenChoice()
                choice.token = self
                choice.reward = reward
                choice.save(force_insert=True)

        return rv


    def redeem(self, reward):

        self.reward = reward
        self.save()


class RewardTokenChoice(poobrains.storage.Model):

    class Meta:

        primary_key = poobrains.storage.CompositeKey('token', 'reward')
        order_by = ['token', 'reward']

    token = poobrains.storage.fields.ForeignKeyField(RewardToken, related_name='reward_choices')
    reward = poobrains.storage.fields.ForeignKeyField(Reward)


class TaskControl(poobrains.auth.Protected):

    user = None
    new = None
    ongoing = None
    finished = None
    aborted = None

    def __init__(self, handle=None, **kwargs):

        super(TaskControl, self).__init__(**kwargs)
        self.user = poobrains.auth.User.load(handle)

        base_query = Task.list('read', poobrains.g.user).where(Task.owner == self.user)
        self.new = base_query.where(Task.status == 'new')
        self.ongoing = base_query.where(Task.status == 'ongoing')
        self.finished = base_query.where(Task.status == 'finished', Task.checkdate > datetime.datetime.now())
        self.aborted = base_query.where(Task.status == 'aborted')


    @property
    def title(self):
        return "%s's goals" % self.user.name


#    def view(self, handle=None, offset=0, **kwargs):
#
#        super(TaskControl, self).view(handle=handle, **kwargs) # checks permissions
#        u = poobrains.auth.User.load(handle)
#
#        q = Task.list('read', poobrains.g.user).where(Task.owner == u, Task.status != 'aborted', Task.status != 'finished').order_by(Task.priority.desc(), Task.checkdate.desc(), Task.created, Task.title)
#
#        listing = poobrains.storage.Listing(Task, title="Your goals", query=q, offset=offset, pagination_options={'handle': handle})
#
#        return listing.view(**kwargs)

app.site.add_view(TaskControl, '/~<handle>/tasks/', mode='full', endpoint='taskcontrol_handle')
app.site.add_view(TaskControl, '/~<handle>/tasks/+<int:offset>', mode='full', endpoint='taskcontrol_handle_offset')


@app.expose('/svg/progress')
class Progress(poobrains.svg.SVG):

    width = '100%'
    height = '20px'

    @property
    def percent(self):
        return int(self.handle)

    def view(self, mode=None, handle=None, **kwargs):
        
        try:
            self.percent # makes sure handle makes sense
            return super(Progress, self).view(mode=mode, handle=handle, **kwargs)
        except TypeError:
            abort(400, 'Progress value must be 0-100.')

@app.route('/')
def front():

    return poobrains.redirect(TaskControl.url(handle=poobrains.g.user.name, mode='full'))


@app.cron
def create_recurring():

    now = datetime.datetime.now()
    dated_tasks = collections.OrderedDict()

    for template in RecurringTask.select():

        try:

            if template.latest_task:
                base_date = template.latest_task.date
            else: # for some reason this can be None without triggering Task.DoesNotExist
                base_date = template.date

        except Task.DoesNotExist:
            base_date = template.date


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

                first_day_of_month = datetime.datetime(year=year, month=month, day=1)

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
                    valid = valid and (not template.weekday_month or day == firstweekday(template.weekday, first_day_of_month.isoweekday()) + (7 * (template.weekday_month -1))) # check if date has correct'th number of weekday occurence in this month (2nd friday or whatev)

                    week_valid = False 
                    if template.weeks:
                        base_monday = datetime.datetime(year=base_date.year, month=base_date.month, day=base_date.day - base_date.weekday())
                        current_monday = dt - datetime.timedelta(days=dt.weekday())

                        delta = current_monday - base_monday
                        if delta.days % (7 * template.weeks) == 0:
                            week_valid = True
                    else:
                        week_valid = True
                
                    #if (first_year_valid or middle_year_valid or last_year_valid) and weekday_valid:
                    if valid and week_valid:
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

                        #weekday_distance = template.weekday - first_day_of_month.isoweekday()

                        week_valid = False 
                        if template.weeks:
                            base_monday = datetime.datetime(year=base_date.year, month=base_date.month, day=base_date.day - base_date.weekday())
                            current_monday = dt - datetime.timedelta(days=dt.weekday())

                            delta = current_monday - base_monday
                            if delta.days % (7 * template.weeks) == 0:
                                week_valid = True
                        else:
                            week_valid = True

                        weekday_valid = not template.weekday or dt.isoweekday() == template.weekday

                        if week_valid and weekday_valid:
                            #weekday_month_valid = not template.weekday_month or (day + weekday_distance) / 7.0 == template.weekday_month - 1
                            weekday_month_valid = not template.weekday_month or day == firstweekday(template.weekday, first_day_of_month.isoweekday()) + (7 * (template.weekday_month -1))

                            if weekday_month_valid: 
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
                task.date = date
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
