from bug import bugzilla_url
from mail import mailing_list_url
from main import ROOT_PATH
from os import path
from snapshot import snapshot_url
from util.common import ensure_directory
from util.common import release_parts
import yaml

def data_load(data_dir):
    bug = None
    mail = None
    snapshot = None

    bug_path = path.join(data_dir, 'bug.yaml')
    if path.exists(bug_path):
        with open(bug_path, 'r') as bug_handle:
            bug = yaml.safe_load(bug_handle)

    mail_path = path.join(data_dir, 'mail.yaml')
    if path.exists(mail_path):
        with open(mail_path, 'r') as mail_handle:
            mail = yaml.safe_load(mail_handle)

    snapshot_path = path.join(data_dir, 'snapshot.yaml')
    if path.exists(snapshot_path):
        with open(snapshot_path, 'r') as snapshot_handle:
            snapshot = yaml.safe_load(snapshot_handle)

    return bug, mail, snapshot

def bug_build(bug_release):
    lines = []

    for bug in sorted(bug_release, key=lambda b: b['id']):
        line = link_format('{}: {}'.format(
            bug['id'], bug['summary']), bugzilla_url(bug['id']))
        if bug['status'] == 'RESOLVED':
            line = '~~{}~~'.format(line)
        lines.append('- ' + line)

    return len(lines), '\n'.join(lines)

def mail_build(mail_release):
    lines = []

    for thread in sorted(mail_release['threads'],
                         key=lambda t: t['reference_count'], reverse=True):
        line = link_format(thread['summary'], mailing_list_url(thread['messages'][0]))
        line += ' ({} refs)'.format(thread['reference_count'])
        extra = []
        for message in thread['messages'][1:]:
            extra.append(link_format(message, mailing_list_url(message)))

        if len(extra):
            line += '; ' + ', '.join(extra)

        lines.append('- ' + line)

    return mail_release['reference_count'], '\n'.join(lines)

def variables_format(variables):
    out = ''
    for key, value in sorted(variables.items()):
        out += '{}: {}\n'.format(key, value)
    return out.strip()

def table_format(headings, data, bold):
    out = []
    out.append(' | '.join(headings))
    out.append(' | '.join(['---'] * len(headings)))
    for key, value in data.items():
        if key in bold:
            key = '**{}**'.format(key)
        out.append(' | '.join([key, value]))
    return '\n'.join(out)

def link_format(text, href):
    return '[{}]({})'.format(text, href)

def posts_build(posts_dir, bug, mail, snapshot):
    template_path = path.join(ROOT_PATH, 'jekyll', '_posts', '.template.md')
    with open(template_path, 'r') as template_handle:
        template = template_handle.read()

    # Likely want to ingest release data as seperate item directly from source.
    for release, mail_release in mail.items():
        reference_count_bug, bug_markdown = bug_build(bug.get(release, []))
        reference_count_mail, mail_markdown = mail_build(mail_release)
        reference_count = reference_count_bug + reference_count_mail

        variables = {
            'release_available': str(release in snapshot).lower(),
            'release_reference_count': reference_count,
            'release_reference_count_mail': reference_count_mail,
            'release_score': 0,
            'release_stability_level': 'unknown',
            'release_version': release,
        }
        links = []

        links.append(link_format('mail announcement', mailing_list_url(mail_release['announcement'])))

        if release in snapshot:
            release_snapshot = snapshot[release]
            for key, value in release_snapshot.items():
                if not key.startswith('binary_interest'):
                    variables['release_{}'.format(key)] = value

            binary_interest = table_format(['Binary', 'Version'], release_snapshot['binary_interest'], release_snapshot['binary_interest_changed'])

            links.append(link_format('binary unique list', snapshot_url(release, 'rpm.unique.list')))
            links.append(link_format('binary list', snapshot_url(release, 'rpm.list')))
        else:
            binary_interest = ''

        if not bug_markdown:
            bug_markdown = 'no relevant bugs'
        if not mail_markdown:
            mail_markdown = 'no relevant mails'

        links = '- ' + '\n- '.join(links)

        post = template.format(
            release=release,
            variables=variables_format(variables),
            bug=bug_markdown,
            bug_count=reference_count_bug,
            mail=mail_markdown,
            mail_count=mail_release['thread_count'],
            binary_interest=binary_interest,
            links=links,
        )

        date = '-'.join(release_parts(release))
        post_name = '{}-release.md'.format(date)
        post_path = path.join(posts_dir, post_name)
        with open(post_path, 'w') as post_handle:
            post_handle.write(post)

def main(args):
    global logger
    logger = args.logger

    posts_dir = path.join(args.output_dir, '_posts')
    ensure_directory(posts_dir)
    data_dir = path.join(args.output_dir, 'data')

    bug, mail, snapshot = data_load(data_dir)
    posts_build(posts_dir, bug, mail, snapshot)

def argparse_configure(subparsers):
    parser = subparsers.add_parser(
        'markdown',
        help='Generate markdown files for Jekyll site.')
    parser.set_defaults(func=main)
