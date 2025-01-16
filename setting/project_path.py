
def project_folder():

    username='balan'
    main_folder = rf"C:\Users\{username}\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review"
    # methodology_json_folder = rf"C:\Users\{username}\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\concept_and_technique"
    # multiple_runs_folder = rf"C:\Users\{username}\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\multiple_runs_temp"
    # final_cross_check_folder = rf"C:\Users\{username}\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\cross_check_final"
    csv_path=rf"C:\Users\{username}\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\database\eeg_review.xlsx"
    path_dict = dict(
        main_folder=main_folder,
        # methodology_json_folder=methodology_json_folder,
        # multiple_runs_folder=multiple_runs_folder,
        # final_cross_check_folder=final_cross_check_folder,
        csv_path=csv_path
    )
    return path_dict