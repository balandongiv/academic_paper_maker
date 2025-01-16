
def project_folder():


    main_folder = r"C:\Users\rpb\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review"

    # Single-run
    methodology_json_folder = r"C:\Users\rpb\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\concept_and_technique"
    multiple_runs_folder = r"C:\Users\rpb\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\multiple_runs_temp"
    final_cross_check_folder = r"C:\Users\rpb\OneDrive - ums.edu.my\research_related\0 eeg_trend_till24\eeg_review\cross_check_final"

    path_dict = dict(
        main_folder=main_folder,
        methodology_json_folder=methodology_json_folder,
        multiple_runs_folder=multiple_runs_folder,
        final_cross_check_folder=final_cross_check_folder
    )
    return path_dict