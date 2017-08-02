class Dir(object):
    def generate_batch(args, dir_path, file_names):
        simp_dir_path = get_simplified_path(args.input_dir, dir_path)
        logging.info("Scanning videos in '%s'", simp_dir_path)
        convertible_files = filter_convertible_files(args, dir_path, file_names)
        track_map = get_track_map(args, dir_path, convertible_files)
        if len(track_map) == 0:
            logging.warning("No videos in '%s' can be converted", simp_dir_path)
            return None
        return BatchInfo(dir_path, track_map)

    def generate_batches(args):
        dir_list = get_files_in_dir(args.input_dir, args.input_formats, args.recursive_search)
        batch_list = []
        found = False
        for dir_path, file_names in dir_list:
            found = True
            batch = generate_batch(args, dir_path, file_names)
            if batch:
                batch_list.append(batch)
        if not found:
            message = "No videos found in input directory"
            if not args.recursive_search:
                message += ", for recursive search specify '-r'"
            logging.info(message)
        return batch_list
