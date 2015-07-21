import click
from tabulate import tabulate
from .factory import create_app
from .models import db
from .models import Task
from .services import TaskService


@click.group()
@click.pass_context
def cli(ctx):
    app = create_app()
    ctx.obj = app

    with app.app_context():
        db.create_all()


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
@click.argument('arguments', nargs=-1)
def list(ctx, app, arguments):
    with app.app_context():
        query = Task.query
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
            click.echo(tabulate(table, headers="keys", tablefmt="pipe"))
        else:
            click.echo("No matching tasks")
