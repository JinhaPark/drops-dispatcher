"""Pure ticketing pre-POST data gate candidate; no IO, transport or origin authority.

The real sender must fetch and verify current private GitHub bytes immediately before
EVERY chunk POST and each rejected-429 retry. No boolean or JSON approval proves that.
"""
from datetime import datetime,timedelta,time
import functools
import hashlib
import json
import re
from zoneinfo import ZoneInfo

SCHEMA='yunchan-queued-notice/v1'
MANAGED='automation-ticketing-prepost/v1'
KINDS={'new_opening','changed_opening','day_before','opening_day'}
INACTIVE={'cancelled','withdrawn','artist_withdrawal','excluded','postponed'}
FIELDS={'schema','notification_id','event_id','phase_id','revision','kind','path','sha256',
        'canonical_event_phase_id','opening_at','opening_timezone','due_date_kst','queued_at',
        'window_start','window_end'}
KST=ZoneInfo('Asia/Seoul')


def need(condition,reason):
    if not condition:raise ValueError('yunchan_dispatch_'+reason)


def guarded(function):
    @functools.wraps(function)
    def wrapped(*args,**kwargs):
        try:return function(*args,**kwargs)
        except (ValueError,TypeError,KeyError,AttributeError,OverflowError,UnicodeError) as error:
            reason=str(error) if isinstance(error,ValueError) else ''
            if not re.fullmatch(r'yunchan_dispatch_[a-z_]+',reason):reason='yunchan_dispatch_invalid_data'
            raise ValueError(reason) from None
    return wrapped


def instant(value):
    need(isinstance(value,str) and 0<len(value)<=80,'timestamp_required')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    need(result.utcoffset() is not None,'timestamp_offset_required')
    return result


def identity(notice):
    need(isinstance(notice,dict),'original_notice_required')
    for key in ('notification_id','revision'):
        need(isinstance(notice.get(key),str) and re.fullmatch(r'[0-9a-f]{64}',notice[key]),'original_identity_required')
    for key in ('event_id','phase_id'):
        value=notice.get(key)
        need(isinstance(value,str) and 0<len(value)<=256 and not any(ord(c)<32 for c in value),'public_identity_required')
    need(notice.get('kind') in KINDS,'kind_invalid')


def enrollment_state(runtime,*,required=False):
    need(isinstance(runtime,dict),'runtime_metadata_required')
    if 'managed_dispatch' not in runtime:
        need(not required,'managed_enrollment_required')
        return 'legacy_unmanaged'
    need(runtime['managed_dispatch']==MANAGED,'managed_enrollment_unknown')
    return 'managed'


def exact_window(notice,queued_at):
    """Only original opening/due dates plus the already authorized caller clock policy."""
    identity(notice)
    opening=instant(notice['opening_at']);zone=ZoneInfo(notice['opening_timezone'])
    need(opening.utcoffset()==opening.astimezone(zone).utcoffset(),'original_timezone_mismatch')
    queued=instant(queued_at)
    need(queued<opening,'opening_passed')
    if notice['kind'] in ('new_opening','changed_opening'):
        need(notice.get('due_date_kst') is None,'initial_due_date_invalid')
        return queued,opening  # No new initial-notice SLA/TTL; strictly before original opening.
    local=opening.astimezone(KST)
    if notice['kind']=='day_before':
        start=datetime.combine(local.date()-timedelta(days=1),time(8),KST)
    else:
        midnight=datetime.combine(local.date(),time(0),KST)
        start=max(midnight,min(datetime.combine(local.date(),time(8),KST),local-timedelta(hours=2)))
    end=min(start+timedelta(seconds=60),opening)
    need(start<end,'no_feasible_same_date_window')
    need(notice.get('due_date_kst')==start.astimezone(KST).date().isoformat(),'original_due_date_mismatch')
    need(start<=queued<end,'publication_outside_due_window')
    return start,end


@guarded
def queued_record(notice,path,source_sha256,canonical_event_phase_id,queued_at):
    """Build bounded body-free metadata; caller commits it with notice+queued ledger."""
    identity(notice)
    need(isinstance(canonical_event_phase_id,str) and
         re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',canonical_event_phase_id),'canonical_path_identity_required')
    expected='reports/general/ticketing/'+canonical_event_phase_id+'-'+notice['revision']+'-'+notice['kind']+'.md'
    need(path==expected and len(path)<=240,'immutable_path_mismatch')
    need(isinstance(source_sha256,str) and re.fullmatch(r'[0-9a-f]{64}',source_sha256),'source_digest_required')
    start,end=exact_window(notice,queued_at)
    value={k:notice.get(k) for k in ('notification_id','event_id','phase_id','revision','kind',
                                    'opening_at','opening_timezone','due_date_kst')}
    value.update(schema=SCHEMA,path=path,sha256=source_sha256,canonical_event_phase_id=canonical_event_phase_id,
                 queued_at=queued_at,window_start=start.isoformat(),window_end=end.isoformat())
    need(set(value)==FIELDS and len(json.dumps(value,ensure_ascii=False).encode())<=4096,'queued_record_bound')
    return value


def strict_ledger(raw):
    need(isinstance(raw,bytes) and 0<len(raw)<=8_000_000,'ledger_bytes_required')
    def pairs(values):
        result={}
        for key,value in values:
            need(key not in result,'duplicate_json_key');result[key]=value
        return result
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
                      parse_constant=lambda _:(_ for _ in ()).throw(ValueError('yunchan_dispatch_nonfinite_json')))


@guarded
def validate_pre_post(ledger_bytes,original_notice,*,report_path,report_bytes,now):
    """Pure necessary data check, NOT proof bytes are fresh or Discord POST authority."""
    identity(original_notice)
    need(isinstance(now,datetime) and now.utcoffset() is not None,'actual_aware_clock_required')
    need(isinstance(report_bytes,bytes) and 0<len(report_bytes)<=50000,'whole_source_bytes_required')
    ledger=strict_ledger(ledger_bytes)
    need(isinstance(ledger,dict) and isinstance(ledger.get('entries'),dict)
         and isinstance(ledger.get('delivery'),dict) and isinstance(ledger.get('caller'),dict),'ledger_shape_invalid')
    runtime=ledger['caller'].get('automation_runtime')
    need(isinstance(runtime,dict) and isinstance(runtime.get('queued_notices'),dict),'legacy_queued_metadata_missing')
    enrollment_state(runtime,required=True)
    notice_id=original_notice['notification_id']
    record=runtime['queued_notices'].get(notice_id)
    need(isinstance(record,dict) and set(record)==FIELDS and record.get('schema')==SCHEMA,'queued_notice_record_missing')
    expected=queued_record(original_notice,report_path,hashlib.sha256(report_bytes).hexdigest(),
                           record['canonical_event_phase_id'],record['queued_at'])
    need(record==expected,'queued_identity_path_digest_window_mismatch')
    need(ledger['delivery'].get(notice_id)=='queued','delivery_not_queued_or_uncertain')
    matches=[(key,value) for key,value in ledger['entries'].items()
             if isinstance(value,dict) and isinstance(value.get('row'),dict)
             and (value['row'].get('event_id'),value['row'].get('phase_id'))==
                 (record['event_id'],record['phase_id'])]
    need(len(matches)==1,'current_original_phase_unresolved')
    key,entry=matches[0];row=entry['row']
    need(key==record['canonical_event_phase_id'] and entry.get('revision')==record['revision'],'current_revision_superseded')
    need(isinstance(row.get('event_status'),str) and row['event_status'] and row['event_status']!='unknown'
         and row.get('event_status') not in INACTIVE and row.get('opening_status')=='confirmed'
         and row.get('source_kind')=='official','current_opening_inactive_or_unconfirmed')
    need(row.get('opening_at')==record['opening_at'] and row.get('opening_timezone')==record['opening_timezone'],
         'current_opening_changed')
    if record['kind'] in ('new_opening','changed_opening'):
        need(isinstance(entry.get('pending'),dict) and entry['pending'].get(notice_id)==original_notice,
             'current_original_pending_missing')
    else:
        intents=runtime.get('reminder_intents')
        need(isinstance(intents,list) and sum(item==original_notice for item in intents)==1,
             'current_original_reminder_missing')
        history=runtime.get('initial_notice_history',[])
        need(isinstance(history,list),'initial_history_unknown')
        need(not any(isinstance(item,dict) and
             (item.get('event_id'),item.get('phase_id'),item.get('revision'),item.get('notice_date_kst'))==
             (record['event_id'],record['phase_id'],record['revision'],now.astimezone(KST).date().isoformat())
             for item in history),'same_day_initial_reminder_collision')
    superseded=runtime.get('superseded_intents',[])
    need(isinstance(superseded,list) and notice_id not in superseded,'intent_superseded')
    need(instant(record['window_start'])<=now<instant(record['window_end'])
         and now<instant(record['opening_at']),'strict_dispatch_window_closed')
    return {'status':'data_matches_gate','notification_id':notice_id,'path':report_path,
            'sha256':record['sha256'],'data_origin_verified':False,'discord_post_authorized':False}
