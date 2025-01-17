from datetime import datetime

import requests
from jinja2 import Environment, FileSystemLoader
from chart_generator import ui_metrics_chart_pages, ui_metrics_chart_actions
from email.mime.image import MIMEImage
from email_notifications import Email


class UIEmailNotification(object):

    def __init__(self, arguments):
        self.test_id = arguments['test_id']
        self.gelloper_url = arguments['galloper_url']
        self.gelloper_token = arguments['token']
        self.galloper_project_id = arguments['project_id']
        self.report_id = arguments['report_id']
        self.test_name = arguments['test']
        self.args = arguments

    def ui_email_notification(self):
        info = self.__get_test_info()
        last_reports = self.__get_last_report(info['name'], 5)
        tests_data = []
        for each in last_reports:
            report = {"pages": [], "actions": []}
            results_info = self.__get_results_info(each["uid"])
            for result in results_info:
                if result["type"] == "page":
                    report["pages"].append(result)
                else:
                    report["actions"].append(result)
            tests_data.append(report)

        page_comparison, action_comparison = [], []
        for index, test in enumerate(tests_data):
            aggregated_test_data = {}
            for metric in ["load_time", "tti", "fvc", "lvc"]:
                _arr = [int(each[metric]) for each in test["pages"]]
                aggregated_test_data[metric] = int(sum(_arr) / len(_arr))
            aggregated_test_data["date"] = last_reports[index]["start_time"][2:-3]
            aggregated_test_data["report"] = f"{self.gelloper_url}/-/performance/ui/results?result_id={last_reports[index]['id']}"
            page_comparison.append(aggregated_test_data)

            aggregated_test_data = {}
            for metric in ["cls", "tbt"]:
                if metric == "cls":
                    _arr = [float(each[metric]) for each in test["actions"]]
                    aggregated_test_data[metric] = float(sum(_arr) / len(_arr)) if len(_arr) else 0
                else:
                    _arr = [int(each[metric]) for each in test["actions"]]
                    aggregated_test_data[metric] = int(sum(_arr) / len(_arr)) if len(_arr) else 0
            aggregated_test_data["date"] = last_reports[index]["start_time"][2:-3]
            aggregated_test_data["report"] = f"{self.gelloper_url}/-/performance/ui/results?result_id={last_reports[index]['id']}"
            action_comparison.append(aggregated_test_data)

        user_list = self.args['user_list']
        date = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        subject = f"[UI] Test results for {info['name']}. From {date}."

        report_info = self.__get_report_info()
        missed_thresholds = round(float(report_info["thresholds_failed"] / report_info["thresholds_total"]) * 100, 2)\
            if report_info["thresholds_total"] else 0
        results_info = self.__get_results_info(self.report_id)
        for each in results_info:
            each["report"] = f"{self.gelloper_url}{each['report'][0]}"

        try:
            baseline_id = self.__get_baseline_report(report_info['name'], report_info['environment'])
            base_id = baseline_id["baseline_id"]
        except:
            base_id = None
        baseline_info = []
        if base_id:
            baseline_info = self.__get_results_info(base_id)
        baseline_comparison_pages = []
        baseline_comparison_actions = []
        aggregated_baseline, aggregated_current_results = [], []
        if baseline_info:
            _baseline_results = {}
            for each in baseline_info:
                if each["identifier"] not in _baseline_results.keys():
                    _baseline_results[each["identifier"]] = {"name": each["name"], "type": each["type"]}
                    if each["type"] == "page":
                        for metric in ["load_time", "fvc", "lvc", "tti"]:
                            _baseline_results[each["identifier"]][metric] = [int(each[metric])]
                    else:
                        for metric in ["tbt", "cls"]:
                            if metric == "tbt":
                                _baseline_results[each["identifier"]][metric] = [int(each[metric])]
                            else:
                                _baseline_results[each["identifier"]][metric] = [float(each[metric])]
                else:
                    if each["type"] == "page":
                        for metric in ["load_time", "fvc", "lvc", "tti"]:
                            _baseline_results[each["identifier"]][metric].append(int(each[metric]))
                    else:
                        for metric in ["tbt", "cls"]:
                            if metric == "tbt":
                                _baseline_results[each["identifier"]][metric].append(int(each[metric]))
                            else:
                                _baseline_results[each["identifier"]][metric].append(float(each[metric]))
            for each in _baseline_results:
                _ = {"identifier": each, "name": _baseline_results[each]["name"], "type": _baseline_results[each]["type"]}
                for metric in ["load_time", "fvc", "lvc", "tti", "tbt", "cls"]:
                    if metric in _baseline_results[each].keys():
                        if metric == "cls":
                            _[metric] = float(sum(_baseline_results[each][metric])/len(_baseline_results[each][metric]))
                        else:
                            _[metric] = int(sum(_baseline_results[each][metric])/len(_baseline_results[each][metric]))
                aggregated_baseline.append(_)

            # TODO refactoring
            _current_results = {}
            for each in results_info:
                if each["identifier"] not in _current_results.keys():
                    _current_results[each["identifier"]] = {"name": each["name"], "type": each["type"]}
                    if each["type"] == "page":
                        for metric in ["load_time", "fvc", "lvc", "tti"]:
                            _current_results[each["identifier"]][metric] = [int(each[metric])]
                    else:
                        for metric in ["tbt", "cls"]:
                            if metric == "tbt":
                                _current_results[each["identifier"]][metric] = [int(each[metric])]
                            else:
                                _current_results[each["identifier"]][metric] = [float(each[metric])]
                else:
                    if each["type"] == "page":
                        for metric in ["load_time", "fvc", "lvc", "tti"]:
                            _current_results[each["identifier"]][metric].append(int(each[metric]))
                    else:
                        for metric in ["tbt", "cls"]:
                            if metric == "tbt":
                                _current_results[each["identifier"]][metric].append(int(each[metric]))
                            else:
                                _current_results[each["identifier"]][metric].append(float(each[metric]))
            for each in _current_results:
                _ = {"identifier": each, "name": _current_results[each]["name"], "type": _current_results[each]["type"]}
                for metric in ["load_time", "fvc", "lvc", "tti", "tbt", "cls"]:
                    if metric in _current_results[each].keys():
                        if metric == "cls":
                            _[metric] = float(
                                sum(_current_results[each][metric]) / len(_current_results[each][metric]))
                        else:
                            _[metric] = int(sum(_current_results[each][metric]) / len(_current_results[each][metric]))
                aggregated_current_results.append(_)

        degradation_rate = 0
        if aggregated_baseline:
            _count = 0
            _failed = 0
            for current_result in aggregated_current_results:
                for baseline_result in aggregated_baseline:
                    if current_result["identifier"] == baseline_result["identifier"]:
                        _count += 1
                        comparison = {"name": current_result["name"]}
                        if current_result["type"] == "page":
                            for each in ["load_time", "fvc", "lvc", "tti"]:
                                comparison[each] = current_result[each]
                                comparison[f"{each}_diff"] = int(current_result[each]) - int(baseline_result[each])
                                if comparison[f"{each}_diff"] > 0:
                                    _failed += 1
                                    comparison[f"{each}_diff"] = f'+{comparison[f"{each}_diff"]}'
                                    comparison[f"{each}_diff_color"] = "color:red;"
                                else:
                                    comparison[f"{each}_diff_color"] = "color:green;"
                            baseline_comparison_pages.append(comparison)
                        else:
                            for each in ["tbt", "cls"]:
                                comparison[each] = current_result[each]
                                if each == "cls":
                                    comparison[f"{each}_diff"] = round(float(current_result[each]) - float(baseline_result[each]), 4)
                                else:
                                    comparison[f"{each}_diff"] = int(current_result[each]) - int(baseline_result[each])
                                if comparison[f"{each}_diff"] > 0:
                                    _failed += 1
                                    comparison[f"{each}_diff"] = f'+{comparison[f"{each}_diff"]}'
                                    comparison[f"{each}_diff_color"] = "color:red;"
                                else:
                                    comparison[f"{each}_diff_color"] = "color:green;"
                            baseline_comparison_actions.append(comparison)
            degradation_rate = round(float(_failed/_count) * 100, 2) if _count else 0

        status = "PASSED"
        error_message = ""
        # TODO get thresholds value from quality gate integration
        if degradation_rate > 1 or missed_thresholds > 1:
            status = "FAILED"
            error_message = f"degradation_rate > 20 %"
        t_params = {
            "scenario": report_info['name'],
            "start_time": report_info["start_time"],
            "status": status,
            "missed_thresholds": missed_thresholds,
            "degradation_rate": degradation_rate,
            "duration": report_info['duration'],
            "env": report_info['environment'],
            "browser": report_info['browser'].capitalize(),
            "version": report_info['browser_version'],
            "view_port": "1920x1080",
            "loops": report_info["loops"],
            "pages": len(results_info)
        }
        email_body = self.__get_email_body(t_params, results_info, page_comparison, action_comparison,
                                           baseline_comparison_pages, baseline_comparison_actions, degradation_rate,
                                           missed_thresholds, error_message)

        charts = []
        charts.append(self.create_ui_metrics_chart_pages(page_comparison))
        charts.append(self.create_ui_metrics_chart_actions(action_comparison))

        return Email(self.test_name, subject, user_list, email_body, charts, date)

    def __extract_recipient_emails(self, info):
        return info['emails'].split(',')

    def __get_test_info(self):
        return self.__get_url(
            f"/ui_performance/test/{self.galloper_project_id}/{self.test_id}?raw=1")

    def __get_baseline_report(self, name, env):
        return self.__get_url(
            f"/ui_performance/baseline/{self.galloper_project_id}?test_name={name}&env={env}")

    def __get_last_report(self, name, count):
        return self.__get_url(f"/ui_performance/reports/{self.galloper_project_id}?name={name}&count={count}")

    def __get_report_info(self):
        return self.__get_url(f"/ui_performance/reports/{self.galloper_project_id}?report_id={self.report_id}")

    def __get_results_info(self, report_id):
        return self.__get_url(f"/ui_performance/results/{self.galloper_project_id}/{report_id}?order=asc")

    def __get_email_body(self, t_params, results_info, page_comparison, action_comparison,
                         baseline_comparison_pages, baseline_comparison_actions, degradation_rate, missed_thresholds,
                         error_message):
        env = Environment(
            loader=FileSystemLoader('./templates'))
        template = env.get_template("ui_email_template.html")
        return template.render(t_params=t_params, results=results_info, page_comparison=page_comparison,
                               action_comparison=action_comparison, baseline_comparison_pages=baseline_comparison_pages,
                               baseline_comparison_actions=baseline_comparison_actions,
                               degradation_rate=degradation_rate, missed_thresholds=missed_thresholds,
                               error_message=error_message)

    def __get_url(self, url):
        resp = requests.get(
            f"{self.gelloper_url}/api/v1{url}", headers={
                'Authorization': f'bearer {self.gelloper_token}',
                'Content-type': 'application/json'
            })

        if resp.status_code != 200:
            raise Exception(f"Error {resp}")

        return resp.json()

    @staticmethod
    def create_ui_metrics_chart_pages(builds):
        labels, x, load_time, tti, fvc, lvc = [], [], [], [], [], []
        count = 1
        for test in builds:
            labels.append(test['date'])
            load_time.append(round(test['load_time'], 2))
            tti.append(round(test['tti'], 2))
            fvc.append(round(test['fvc'], 2))
            lvc.append(round(test['lvc'], 2))
            x.append(count)
            count += 1
        datapoints = {
            'title': 'UI metrics',
            'label': 'UI metrics',
            'x_axis': 'Test Runs',
            'y_axis': 'Time, ms',
            'width': 14,
            'height': 4,
            'path_to_save': '/tmp/ui_metrics_pages.png',
            'total_time': load_time[::-1],
            'tti': tti[::-1],
            'fvc': fvc[::-1],
            'lvc': lvc[::-1],
            'values': x,
            'labels': labels[::-1]
        }
        ui_metrics_chart_pages(datapoints)
        fp = open('/tmp/ui_metrics_pages.png', 'rb')
        image = MIMEImage(fp.read())
        image.add_header('Content-ID', '<ui_metrics_pages>')
        fp.close()
        return image

    @staticmethod
    def create_ui_metrics_chart_actions(builds):
        labels, x, cls, tbt = [], [], [], []
        count = 1
        for test in builds:
            labels.append(test['date'])
            cls.append(round(test['cls'], 6))
            tbt.append(round(test['tbt'], 2))
            x.append(count)
            count += 1
        datapoints = {
            'title': 'UI metrics Actions',
            'label': 'UI metrics Actions',
            'x_axis': 'Test Runs',
            'y_axis': 'Time, ms',
            'width': 14,
            'height': 4,
            'path_to_save': '/tmp/ui_metrics_actions.png',
            'cls': cls[::-1],
            'tbt': tbt[::-1],
            'values': x,
            'labels': labels[::-1]
        }
        ui_metrics_chart_actions(datapoints)
        fp = open('/tmp/ui_metrics_actions.png', 'rb')
        image = MIMEImage(fp.read())
        image.add_header('Content-ID', '<ui_metrics_actions>')
        fp.close()
        return image
