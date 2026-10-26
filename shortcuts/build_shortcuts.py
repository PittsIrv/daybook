#!/usr/bin/env python3
"""Build collectors from the user's actual exported Screen Time action.

Uses only Python's standard library; does not install or schedule anything.
Apple's shortcuts sign command signs the resulting importable files separately.
"""
from copy import deepcopy
from pathlib import Path
import plistlib
import uuid

ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / 'source/original.shortcut'
SOURCE = plistlib.loads(SOURCE_PATH.read_bytes()) if SOURCE_PATH.exists() else None
GENERIC = {'WFWorkflowMinimumClientVersion':900, 'WFWorkflowMinimumClientVersionString':'900',
           'WFWorkflowClientVersion':'5037.0.19',
           'WFWorkflowIcon':{'WFWorkflowIconStartColor':-615917313,'WFWorkflowIconGlyphNumber':61440},
           'WFWorkflowActions':[], 'WFWorkflowOutputContentItemClasses':[],
           'WFWorkflowHasOutputFallback':False, 'WFQuickActionSurfaces':[]}
OUT = ROOT / 'build'
OUT.mkdir(exist_ok=True)


def uid(label):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'screen-time-snapshot/v1/' + label)).upper()


def reference(label, name):
    return {'Type': 'ActionOutput', 'OutputUUID': uid(label), 'OutputName': name}


def attachment(value):
    return {'WFSerializationType': 'WFTextTokenAttachment', 'Value': value}


def text(*parts):
    string, attachments = '', {}
    for part in parts:
        if isinstance(part, dict):
            position = len(string.encode('utf-16-le')) // 2
            attachments[f'{{{position}, 1}}'] = part
            string += '\ufffc'
        else:
            string += part
    return {'WFSerializationType': 'WFTextTokenString',
            'Value': {'string': string, 'attachmentsByRange': attachments}}


def action(identifier, label=None, **params):
    if label:
        params['UUID'] = uid(label)
    return {'WFWorkflowActionIdentifier': identifier,
            'WFWorkflowActionParameters': params}


def make(period='today', save=True, portable=False):
    source = GENERIC if portable or SOURCE is None else SOURCE
    a = []
    add = a.append
    add(action('is.workflow.actions.comment', WFCommentActionText=(
        'One snapshot per run. No timer loop and no Full Disk Access.\n'
        'Before first use, expand Get App & Website Activity and select your device scope.\n'
        'First run: verify the device scope and the app/duration text.\n'
        'Stores original activity text inside a JSON envelope; numeric per-app '
        'parsing is intentionally not assumed. Schedule on your iPhone separately.')))
    add(action('is.workflow.actions.date', 'capture-date', WFDateActionMode='Current Date'))
    date = reference('capture-date', 'Date')
    for label, fmt in [('capture-iso', "yyyy-MM-dd'T'HH:mm:ss.SSSXXXXX"),
                       ('file-stamp', 'yyyyMMdd-HHmmss-SSS')]:
        add(action('is.workflow.actions.format.date', label, WFDate=text(date),
                   WFDateFormatStyle='Custom', WFDateFormat=fmt, WFTimeFormatStyle='None'))
    if period == 'yesterday':
        add(action('is.workflow.actions.adjustdate', 'report-date', WFDate=text(date),
                   WFAdjustOperation='Subtract', WFDuration={'Value': {'Magnitude': 1, 'Unit': 'days'},
                   'WFSerializationType': 'WFQuantityFieldValue'}))
        date_for_report = reference('report-date', 'Adjusted Date')
    else:
        date_for_report = date
    add(action('is.workflow.actions.format.date', 'report-day', WFDate=text(date_for_report),
               WFDateFormatStyle='Custom', WFDateFormat='yyyy-MM-dd', WFTimeFormatStyle='None'))
    add(action('is.workflow.actions.getdevicedetails', 'collector', WFDeviceDetail='Device Name'))
    if source is GENERIC:
        usage = action('com.apple.intelligenceplatform.IntelligencePlatform.IntelligencePlatformDataActionsAppIntentsExtension.CalculateAppUsageIntent')
    else:
        usage = deepcopy(next(x for x in source['WFWorkflowActions']
                              if x['WFWorkflowActionIdentifier'].endswith('.CalculateAppUsageIntent')))
    usage['WFWorkflowActionParameters']['during'] = period
    usage['WFWorkflowActionParameters']['UUID'] = uid('usage')
    add(usage)
    # Keep the user's repeat/combine conversion, with an explicit Text action
    # inside the loop so every returned activity is consumed.
    group = uid('activity-loop')
    add(action('is.workflow.actions.repeat.each', WFInput=attachment(reference('usage', 'Activity')),
               GroupingIdentifier=group, WFControlFlowMode=0))
    add(action('is.workflow.actions.gettext', 'item-text',
               WFTextActionText=text({'Type': 'Variable', 'VariableName': 'Repeat Item'})))
    add(action('is.workflow.actions.repeat.each', 'repeat-results',
               GroupingIdentifier=group, WFControlFlowMode=2))
    add(action('is.workflow.actions.text.combine', 'combined', WFTextSeparator='New Lines',
               text=attachment(reference('repeat-results', 'Repeat Results'))))
    fields = {
        'schema_version': '1',
        'captured_at': reference('capture-iso', 'Formatted Date'),
        'report_date': reference('report-day', 'Formatted Date'),
        'query_period': period,
        'collector_device': reference('collector', 'Device Details'),
        'device_scope': 'configured_device' if source is GENERIC else 'all_devices',
        'measurement': 'cumulative_daily_usage',
        'activity_encoding': 'shortcuts_text',
        'raw_activity_text': reference('combined', 'Combined Text'),
    }
    items = [{'WFItemType': 0, 'WFKey': text(k), 'WFValue': text(v)} for k, v in fields.items()]
    add(action('is.workflow.actions.dictionary', 'snapshot', WFItems={
        'WFSerializationType': 'WFDictionaryFieldValue',
        'Value': {'WFDictionaryFieldValueItems': items}}))
    add(action('is.workflow.actions.gettext', 'json',
               WFTextActionText=text(reference('snapshot', 'Dictionary'))))
    if save:
        add(action('is.workflow.actions.file.createfolder', 'folder', WFFilePath='ScreenTime/snapshots'))
        add(action('is.workflow.actions.documentpicker.save', 'saved',
                   WFInput=attachment(reference('json', 'Text')),
                   WFAskWhereToSave=False, WFSaveFileOverwrite=False,
                   WFFileDestinationPath=text('ScreenTime/snapshots/',
                       reference('file-stamp', 'Formatted Date'), '-',
                       reference('collector', 'Device Details'), '-', period, '.txt')))
    add(action('is.workflow.actions.output', WFOutput=text(reference('json', 'Text')),
               WFNoOutputSurfaceBehavior='Do Nothing'))
    workflow = deepcopy(source)
    workflow['WFWorkflowActions'] = a
    workflow['WFWorkflowTypes'] = []
    workflow['WFWorkflowInputContentItemClasses'] = []
    workflow['WFWorkflowImportQuestions'] = []
    workflow['WFWorkflowHasShortcutInputVariables'] = False
    return workflow


def validate(workflow):
    """Check graph references and enforce the no-wait/no-network collector boundary."""
    seen = set()
    def refs(value):
        if isinstance(value, dict):
            if value.get('Type') == 'ActionOutput':
                yield value['OutputUUID']
            for child in value.values():
                yield from refs(child)
        elif isinstance(value, list):
            for child in value:
                yield from refs(child)
    for item in workflow['WFWorkflowActions']:
        identifier = item['WFWorkflowActionIdentifier']
        assert identifier not in {'is.workflow.actions.delay', 'is.workflow.actions.repeat.count',
                                  'is.workflow.actions.downloadurl', 'is.workflow.actions.setstoredcontent'}
        params = item['WFWorkflowActionParameters']
        for ref in refs(params):
            assert ref in seen, f'Dangling or forward reference: {ref}'
        if 'UUID' in params:
            assert params['UUID'] not in seen
            seen.add(params['UUID'])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--portable', action='store_true', help='Exclude personal source metadata and device identifiers')
    args = parser.parse_args()
    if args.portable:
        OUT = ROOT / 'release'
        OUT.mkdir(exist_ok=True)
    for name, period, save in [('Screen Time Snapshot', 'today', True),
                               ('Screen Time Yesterday', 'yesterday', True),
                               ('Screen Time Check', 'today', False)]:
        workflow = make(period, save, portable=args.portable)
        validate(workflow)
        path = OUT / (name + '.unsigned.shortcut')
        path.write_bytes(plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY, sort_keys=False))
        print(f'Built {path.name}: {len(workflow["WFWorkflowActions"])} actions; references valid')
