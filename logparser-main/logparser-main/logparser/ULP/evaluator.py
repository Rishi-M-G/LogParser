import pandas as pd
import scipy.special
from nltk.metrics.distance import edit_distance
from sklearn.metrics import accuracy_score
import numpy as np


def evaluate(groundtruth, parsedresult):
    df_groundtruth = pd.read_csv(groundtruth)
    df_parsedlog = pd.read_csv(parsedresult, index_col=False)
    #df_groundtruth['EventTemplate'] = df_groundtruth['EventTemplate'].str.lower()

    # Remove invalid groundtruth event Ids
    null_logids = df_groundtruth[~df_groundtruth['EventTemplate'].isnull()].index
    df_groundtruth = df_groundtruth.loc[null_logids]
    df_parsedlog = df_parsedlog.loc[null_logids]

    accuracy_exact_string_matching = accuracy_score(np.array(df_groundtruth.EventTemplate.values, dtype='str'),
                                                    np.array(df_parsedlog.EventTemplate.values, dtype='str'))

    edit_distance_result = []
    for i, j in zip(np.array(df_groundtruth.EventTemplate.values, dtype='str'),
                    np.array(df_parsedlog.EventTemplate.values, dtype='str')):
        edit_distance_result.append(edit_distance(i, j))

    edit_distance_result_mean = np.mean(edit_distance_result)
    edit_distance_result_std = np.std(edit_distance_result)

    (precision, recall, f_measure, accuracy_PA) = get_accuracy(df_groundtruth['EventTemplate'],
                                                               df_parsedlog['EventTemplate'])

    msg_accuracy = evaluate_message_level(
        groundtruth=df_groundtruth,
        parsedresult=df_parsedlog
    )

    unseen_events = df_groundtruth.EventTemplate.value_counts()
    df_unseen_groundtruth = df_groundtruth[df_groundtruth.EventTemplate.isin(unseen_events.index[unseen_events.eq(1)])]
    df_unseen_parsedlog = df_parsedlog[df_parsedlog.LineId.isin(df_unseen_groundtruth.LineId.tolist())]
    n_unseen_logs = len(df_unseen_groundtruth)
    if n_unseen_logs == 0:
        unseen_PA = 0
    else:
        unseen_PA = accuracy_score(np.array(df_unseen_groundtruth.EventTemplate.values, dtype='str'),
                                   np.array(df_unseen_parsedlog.EventTemplate.values, dtype='str'))
    print(
        'Precision: %.4f, Recall: %.4f, F1_measure: %.4f, Group Accuracy: %.4f, Message-Level Accuracy: %.4f, Edit Distance: %.4f' % (
            precision, recall, f_measure, accuracy_PA, msg_accuracy, edit_distance_result_mean))

    return accuracy_PA, msg_accuracy, edit_distance_result_mean, edit_distance_result_std, unseen_PA, n_unseen_logs


def get_accuracy(series_groundtruth, series_parsedlog, debug=False):
    series_groundtruth_valuecounts = series_groundtruth.value_counts()
    real_pairs = 0
    for count in series_groundtruth_valuecounts:
        if count > 1:
            real_pairs += scipy.special.comb(count, 2)

    series_parsedlog_valuecounts = series_parsedlog.value_counts()
    parsed_pairs = 0
    for count in series_parsedlog_valuecounts:
        if count > 1:
            parsed_pairs += scipy.special.comb(count, 2)

    accurate_pairs = 0
    accurate_events = 0  # determine how many lines are correctly parsed
    for parsed_eventId in series_parsedlog_valuecounts.index:
        logIds = series_parsedlog[series_parsedlog == parsed_eventId].index
        series_groundtruth_logId_valuecounts = series_groundtruth[logIds].value_counts()
        error_eventIds = (parsed_eventId, series_groundtruth_logId_valuecounts.index.tolist())
        error = True
        if series_groundtruth_logId_valuecounts.size == 1:
            groundtruth_eventId = series_groundtruth_logId_valuecounts.index[0]
            if logIds.size == series_groundtruth[series_groundtruth == groundtruth_eventId].size:
                accurate_events += logIds.size
                error = False
        if error and debug:
            print('(parsed_eventId, groundtruth_eventId) =', error_eventIds, 'failed', logIds.size, 'messages')
        for count in series_groundtruth_logId_valuecounts:
            if count > 1:
                accurate_pairs += scipy.special.comb(count, 2)

    precision = float(accurate_pairs) / parsed_pairs
    recall = float(accurate_pairs) / real_pairs
    f_measure = 2 * precision * recall / (precision + recall)
    accuracy = float(accurate_events) / series_groundtruth.size
    return precision, recall, f_measure, accuracy

def evaluate_message_level(groundtruth, parsedresult):
    msg_groundtruth = groundtruth['EventTemplate'].values.astype('str')
    msg_parsedlog = parsedresult['EventTemplate'].values.astype('str')

    msg_groundtruth = np.char.strip(np.char.lower(msg_groundtruth))
    msg_parsedlog = np.char.strip(np.char.lower(msg_parsedlog))

    # print("Groundtruth:", msg_groundtruth)
    # print("Parsed Log:", msg_parsedlog)

    # Message-level accuracy
    def clean_string(s):
        return ''.join(c for c in s if c.isalnum())
    #msg_accuracy = np.mean(msg_groundtruth == msg_parsedlog)
    correct_predictions = np.sum([clean_string(msg) == clean_string(parsed) for msg, parsed in zip(msg_groundtruth, msg_parsedlog)])
    total_predictions = len(msg_groundtruth)
    msg_accuracy = correct_predictions / total_predictions if total_predictions != 0 else 0


    # print("Correct Predictions:", correct_predictions)
    # print("Total Predictions:", total_predictions)
    # print("Message-Level Accuracy:", msg_accuracy)


    return msg_accuracy