import click
import arrow
from tabulate import tabulate
from .factory import create_app
from .models import Task, Project
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
        query = query.filter(Task.waituntil <= arrow.now())
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
