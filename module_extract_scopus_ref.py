from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, \
    InvalidArgumentException
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup as Soup
import re
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import time

'''
To try at cisir PC
today friday
successfully tested on 02 July 2020
'''


class ScrapeScopus:
    def __init__(self, to_url, descendent_level=None):

        self.descendent_level = 1 if descendent_level is None else descendent_level
        # print("Start the setup")
        chrome_options = webdriver.ChromeOptions()

        # Load current user default profile
        # current_user=get_username()
        # current_user = getuser()
        current_user = 'balan'
        chrome_options.add_argument(
            r"--user-data-dir=C:\Users\{}\AppData\Local\Google\Chrome\User Data".format(current_user))
        self.browser = webdriver.Chrome(
            executable_path=r"C:Browsers\chromedriver.exe",
            options=chrome_options)

        self.to_url = to_url

    @staticmethod
    def scrape_individual_result(document_idx, page_soup):
        '''
        This is the slow approach to scrape each row of the article.
        Obselete
        '''

        try:
            paper_href_scopus = page_soup.select(f'#resultDataRow{document_idx:d} > td:nth-child(2) > a')[0]['href']
        except (NoSuchElementException, IndexError) as e:
            paper_href_scopus = 'NOT AVAILABLE'

        try:
            paper_title = page_soup.select(f'#resultDataRow{document_idx:d} > td:nth-child(2) > a')[0].text
        except (NoSuchElementException, IndexError) as e:
            paper_title = 'NOT AVAILABLE'

        try:
            paper_year = page_soup.select(f'#resultDataRow{document_idx:d} > td:nth-child(4) > span')[0].text
        except (NoSuchElementException, IndexError) as e:
            paper_year = 'NOT AVAILABLE'

        try:
            paper_publisher_link_paper = \
                page_soup.select(f'#resultLinkRow{document_idx:d} > td > ul > li:nth-child(2) > '
                                 f'span.divTextLink > a')[0]['href']
        except (NoSuchElementException, IndexError) as e:
            paper_publisher_link_paper = 'NOT AVAILABLE'

        paper_author = []

        for author_idx in range(1, 2):  # limit to first three author to speed up
            try:
                paper_author.append(page_soup.select(f'#resultDataRow{document_idx:d} > td:nth-child(3) > span > '
                                                     f'a:nth-child({author_idx:d})')[0].text)
            except IndexError:
                break

        document_status = dict(paper_title=paper_title, paper_year=paper_year,
                               paper_author=paper_author, paper_publisher_link_paper=paper_publisher_link_paper,
                               paper_href_scopus=paper_href_scopus)
        return document_status

    @staticmethod
    def extract_default_info(page_soup):
        '''
        Used to extract from the individual page
        '''
        try:
            results_doc_journal = page_soup.find_all("a", {"title": "Go to the information page for this source"})
            if not results_doc_journal:
                try:
                    document_journal = page_soup.find("span", {"id": "noSourceTitleLink"}).text
                except:
                    document_journal = 'NOT AVAILABLE'
            else:
                for result in results_doc_journal:
                    document_journal = result.find('span', attrs={'class': 'anchorText'}).text  # result not results
        except (NoSuchElementException, IndexError, UnboundLocalError) as e:
            document_journal = 'NOT AVAILABLE'

        try:
            document_abstract = page_soup.select('#abstractSection > p')[0].text
        except (NoSuchElementException, IndexError) as e:
            document_abstract = 'NOT AVAILABLE'

        try:
            document_doi = page_soup.select('#recordDOI')[0].text
        except (NoSuchElementException, IndexError) as e:
            document_doi = 'NOT AVAILABLE'

        try:
            document_publisher = re.split(r"Publisher:", page_soup.select('#documentInfo > li:nth-child(4)')[0].text)[1]
        except (NoSuchElementException, IndexError) as e:
            document_publisher = 'NOT AVAILABLE'

        try:
            document_type = re.split(r"Document Type:", page_soup.select('#documentInfo > li:nth-child(3)')[0].text)[1]
        except (NoSuchElementException, IndexError) as e:
            document_type = 'NOT AVAILABLE'

        try:
            document_volume_issue_year = page_soup.select('#articleTitleInfo > span.list-group-item')[1].text
        except (NoSuchElementException, IndexError) as e:
            document_volume_issue_year = 'NOT AVAILABLE'

        if document_volume_issue_year.find('Volume') != -1:
            document_volume = document_volume_issue_year.split('Volume')[1].split(',')[0]
        else:
            document_volume = 'NA'

        if document_volume_issue_year.find('Issue') != -1:
            document_issue = document_volume_issue_year.split('Issue')[1].split(',')[0]
        else:
            document_issue = 'NA'

        if document_volume_issue_year.find('Pages') != -1:
            document_number = document_volume_issue_year.split('Pages')[1].split(',')[0]
        else:
            document_number = 'NA'

        try:
            document_year = document_volume_issue_year.split('Issue')[1].split(',')[1]
        except (NoSuchElementException, IndexError) as e:
            split_str = document_volume_issue_year.split(',')
            try:
                document_year = split_str[2]
            except (NoSuchElementException, IndexError) as e:
                document_year = 'NOT AVAILABLE'

        try:
            author_names = []
            page_soup_section = page_soup.find("section", {"id": "authorlist"}).find_all("span",
                                                                                         {"class": "anchorText"})
            for author_lt in page_soup_section:
                author_names.append(author_lt.text.split('.')[0])
        except NoSuchElementException:
            author_names = 'NOT AVAILABLE'

        document_report = dict(document_abstract=document_abstract, document_doi=document_doi,
                               document_publisher=document_publisher, document_type=document_type,
                               document_volume=document_volume, document_issue=document_issue,
                               document_year=document_year, document_number=document_number, author_names=author_names,
                               document_journal=document_journal)

        return document_report

    def clear_cache(self):
        self.browser.get('chrome://settings/clearBrowserData')
        self.browser.find_element_by_xpath('//settings-ui').send_keys(Keys.ENTER)

    @staticmethod
    def filter_by_type(list_to_test, type_of):
        return [n for n in list_to_test if isinstance(n, type_of)]

    def move_next_page(self, page_soup_search_result):

        page_current_page_old = int(page_soup_search_result.find(attrs={"name": "currentPage"})['value'])
        list_page_visible = self.get_available_page(page_soup_search_result)
        shift_no_page = 3

        page_current_page_new = page_current_page_old + 1
        index_location = list_page_visible.index(page_current_page_new)
        current_page_no = shift_no_page + index_location
        some_termination_condition = []
        attempt_to_refresh = 0
        refresh_error = []
        while some_termination_condition != 1:
            try:
                WebDriverWait(self.browser, 8).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, f'#resultsFooter > '
                                                                       f'div.col-md-6.center-block.text-center > '
                                                                       f'ul > li:nth-child({current_page_no:d}) > '
                                                                       f'a '))).click()
                page_soup_search_result = Soup(self.browser.page_source, 'html.parser')

                # Check current page if similar to our intended page
                try:
                    page_current_page = int(page_soup_search_result.find(attrs={"name": "currentPage"})['value'])

                    if page_current_page == page_current_page_new:
                        some_termination_condition = 1
                        # print('yes, intended page')
                    else:
                        # print('repeat the procedure until the requirement is satisfied')
                        if attempt_to_refresh == 2:
                            refresh_error = 'Custom_refresh_error'
                            some_termination_condition = 1
                        else:
                            attempt_to_refresh = attempt_to_refresh + 1
                            self.browser.back()

                except TypeError:
                    if attempt_to_refresh == 2:
                        refresh_error = 'Custom_refresh_error'
                        some_termination_condition = 1
                        page_current_page = 1000000
                    else:
                        attempt_to_refresh = attempt_to_refresh + 1
                        self.browser.back()

            except (
                    NoSuchElementException, TimeoutException, IndexError, ElementClickInterceptedException,
                    TypeError) as e:
                # continue
                if attempt_to_refresh == 2:
                    refresh_error = 'Custom_refresh_error'
                    page_current_page = 1000000
                    continue
                else:
                    attempt_to_refresh = attempt_to_refresh + 1
                    self.browser.back()

                    refresh_error = 'Custom_refresh_error'
                    page_current_page = 1000000

        return page_soup_search_result, page_current_page, refresh_error

    @staticmethod
    def get_available_page(page_soup_search_result):
        list_page_visible = []
        for div_tag in page_soup_search_result.find_all('div', {'class': 'col-md-6 center-block text-center'}):
            for litag in div_tag.find_all('li'):
                str_litag = litag.text
                try:
                    list_page_visible.append(int(str_litag))
                except ValueError:
                    list_page_visible.append('NA')
        return list_page_visible

    def scrape_scopus(self, to_url):
        try:
            self.browser.get(to_url)
            WebDriverWait(self.browser, 30).until(EC.visibility_of_element_located(
                (By.CSS_SELECTOR, '#gh-branding'))).get_attribute('href')  # Just to make sure page load properly

            page_soup = Soup(self.browser.page_source, 'html.parser')
            document_reports = self.extract_default_info(page_soup)

            if self.descendent_level != 1:
                try:
                    href_str = WebDriverWait(self.browser, 30).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, '#referenceSrhResults'))).get_attribute('href')
                except (NoSuchElementException, TimeoutException, IndexError) as e:
                    return dict(all_result=[], document_reports=[])

                self.browser.get(href_str)
                all_result_x = self.scrape_scopus_multi_search()
            else:
                all_result_x = []

        except InvalidArgumentException:
            all_result_x = []
            document_reports = []

        return all_result_x, document_reports

    def scrape_scopus_multi_search(self):

        page_soup_search_result = Soup(self.browser.page_source, 'html.parser')  # To parse the search result
        last_page = max(self.filter_by_type(self.get_available_page(page_soup_search_result), int))

        result_per_page = int(
            page_soup_search_result.select('#resultsPerPage-button > span.ui-selectmenu-text')[0].text)

        current_page_no_actual = int(page_soup_search_result.find(attrs={"name": "currentPage"})['value'])

        some_termination_condition = []
        all_result_x = []
        while some_termination_condition != 1:
            try:
                for document_index in range(0, result_per_page):
                    try:
                        document_status_x = self.scrape_individual_result(document_index, page_soup_search_result)

                    except IndexError:
                        document_status_x = dict(paper_title='NA', paper_year='NA', paper_author='NA',
                                                 paper_publisher_link_paper='NA', paper_href_scopus='NA')

                    all_result_x.append(document_status_x)

                try:
                    if current_page_no_actual != last_page:
                        page_soup_search_result, current_page_no_actual, refresh_error = self.move_next_page(
                            page_soup_search_result)
                        if refresh_error == 'Custom_refresh_error':
                            some_termination_condition = 1
                    else:
                        break

                except (NoSuchElementException, TimeoutException, ElementClickInterceptedException) as e:
                    page_soup_page_verification = Soup(self.browser.page_source, 'html.parser')
                    page_current_page_verification = int(
                        page_soup_page_verification.find(attrs={"name": "currentPage"})['value'])

                    if page_current_page_verification == last_page:
                        some_termination_condition = 1
                        current_page_no_actual = page_current_page_verification
                        continue

            except IndexError:
                some_termination_condition = 1

            if current_page_no_actual % 5 == 0:
                print(f"complete page {current_page_no_actual:d} out of {last_page:d}")

        return all_result_x

    @property
    def loop_url_second(self):
        all_url_list = self.to_url
        all_result = []

        try:
            for to_url in all_url_list:
                self.browser.get(to_url)
                report_status = self.scrape_scopus_multi_search()
                all_result.append(report_status)

            self.browser.quit()
        except (NoSuchElementException, TimeoutException, IndexError) as e:
            self.browser.quit()
            all_result = []

        return all_result

    @property
    def loop_url(self):
        all_url_list = self.to_url

        for idx_href in range(0, len(all_url_list)):
            to_url = all_url_list[idx_href]['paper_href_scopus']
            all_result_x, document_reports = self.scrape_scopus(to_url)
            all_url_list[idx_href]['secondary_citing_paper'] = all_result_x
            all_url_list[idx_href]['detail_paper_bib'] = document_reports
        # exception_must_integer = 'string indices must be integers'
        # try:
        #     # for idx_href in range(0, 4):
        #     xx = len(all_url_list)
        #     for idx_href in range(0, len(all_url_list)):
        #         to_url = all_url_list[idx_href]['paper_href_scopus']
        #         all_result_x, document_reports = self.scrape_scopus(to_url)
        #         all_url_list[idx_href]['secondary_citing_paper'] = all_result_x
        #         all_url_list[idx_href]['detail_paper_bib'] = document_reports
        #
        #
        # # except (TimeoutException, IndexError) as e:
        # except Exception as exception:
        #     all_url_list_temp = []
        #     catch_exception_list = ("{}".format(exception))
        #     if catch_exception_list == exception_must_integer:
        #         for to_url in all_url_list:
        #             '''
        #             TODO
        #             To use index as we need to append specifically to
        #             ['secondary_citing_paper']  and  ['detail_paper_bib']
        #             '''
        #             all_result_x, document_reports = self.scrape_scopus(to_url)
        #             all_url_list_temp.append(dict(all_result_x=all_result_x, document_reports=document_reports))
        #
        #     all_url_list = all_url_list_temp

        self.cleanup_process()

        return all_url_list

    def cleanup_process(self):
        self.browser.close()
        self.browser.quit()
