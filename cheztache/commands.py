import click
from .factory import create_app
from .models import db
from .models import Task


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
    description = []
    tags = []
    for arg in arguments:
        if ':' in arg:
            pass
        elif arg.startswith('+'):
            tags.append(arg[1:])
        else:
            description.append(arg)

    if not description:
        return ctx.fail("Invalid task description")

    with app.app_context():
        description = ' '.join(description)
        task = Task(description=description)
        db.session.add(task)
        db.session.commit()


@cli.command()
@click.pass_obj
@click.pass_context
@click.argument('arguments', nargs=-1)
def list(ctx, app, arguments):
    with app.app_context():
        query = Task.query
        if query.count():
            click.echo('{0} | {1}'.format('#', 'Description'))
        for task in query:
            click.echo('{0} | {1}'.format(task.number, task.description))
