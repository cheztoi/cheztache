import click
import arrow
import sqlalchemy
from sqlalchemy.sql import or_
from tabulate import tabulate
from .factory import create_app
from .models import db, Task, Project
from .services import TaskService, ProjectService


@click.group()
@click.pass_context
def cli(ctx):
    app = create_app()
    ctx.obj = app


@cli.command()
@click.pass_obj
def runserver(app):
    app.run()


@cli.command()
@click.pass_obj
@click.pass_context
@click.argument('arguments', nargs=-1)
def add(ctx, app, arguments):
    with app.app_context():
        ts = TaskService()
        try:
            task = ts.from_arguments(arguments)
            click.echo('Task {} created'.format(task.number))
        except Exception as ex:
            ctx.fail(ex.message)


@cli.command()
@click.pass_obj
@click.pass_context
@click.option('--projects', is_flag=True, help="List projects")
@click.argument('arguments', nargs=-1)
def list(ctx, app, projects, arguments):
    with app.app_context():
        if projects:
            for project in Project.query:
                click.echo(project.name)
            return

        ts = TaskService()
        defaults = ''
        query = ts.filter_by_arguments(arguments, defaults=defaults)
        query = query.filter(Task.completed == None)  # noqa
        query = query.filter(
            or_(Task.waituntil <= arrow.now(), Task.waituntil == None))  # noqa
        if query.count():
            table = {
                '#': [],
                'Pro': [],
                'Description': [],
            }
            for task in query:
                table['#'].append(task.number)
                table['Pro'].append(task.project.name if task.project else '')
                table['Description'].append(task.description)
            click.echo(tabulate(table, headers="keys"))
        else:
            click.echo("No matching tasks")


@cli.command()
@click.pass_obj
@click.pass_context
@click.argument('ids', nargs=-1)
def done(ctx, app, ids):
    arguments = ids
    ids = []
    for arg in arguments:
        for i in arg.split(','):
            if i:
                try:
                    ids.append(int(i))
                except ValueError:
                    click.echo('Invalid task number: {}'.format(i))
                    ctx.exit()
    ids = set(ids)
    if not ids:
        return ctx.fail("No tasks ids defined")

    with app.app_context():
        tasks = []
        for i in ids:
            try:
                task = Task.query.filter(Task.number == i).one()
                tasks.append(task)
            except sqlalchemy.orm.exc.NoResultFound:
                click.echo("Invalid task id: {}".format(i))
                ctx.exit()

        now = arrow.now()
        for task in tasks:
            task.completed = now
            db.session.add(task)
        db.session.commit()


@cli.group()
def create():
    pass


@create.command()
@click.pass_obj
@click.pass_context
@click.argument('name', nargs=1)
def project(ctx, app, name):
    with app.app_context():
        ps = ProjectService()
        project = ps.get_or_create(name=name)
        click.echo("Created project: {}".format(project.name))
