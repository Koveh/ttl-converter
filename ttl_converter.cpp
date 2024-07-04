#include <iostream>
#include <fstream>
#include <vector>
#include <unordered_map>
#include <regex>
#include <string>
#include <algorithm>
#include <sstream>
#include <chrono>
#include <numeric>

const std::vector<std::string> STATEMENT_PREFIX = {"v:", "s:", "ref:"};
const std::vector<std::string> TRIPLE_STATEMENT_PREFIX = {"p:", "psv:"};

std::string preprocess_ttl(const std::string& ttl_text) {
    std::regex whitespace_regex("\\s+");
    std::regex semicolon_regex("([;,])(?!\\s)");
    std::regex period_regex("\\s+\\.");

    std::string preprocessed = std::regex_replace(ttl_text, whitespace_regex, " ");
    preprocessed = std::regex_replace(preprocessed, semicolon_regex, "$1 ");
    preprocessed = std::regex_replace(preprocessed, period_regex, " .");

    preprocessed = std::regex_replace(preprocessed, std::regex("^\\s+|\\s+$"), "");
    
    if (!preprocessed.empty() && preprocessed.back() == '.') {
        preprocessed.pop_back();
    }

    return preprocessed;
}

std::vector<std::string> split_by_periods_keep_quotes(const std::string& text) {
    std::regex pattern("\\.\\s+(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)");
    std::vector<std::string> sections(
        std::sregex_token_iterator(text.begin(), text.end(), pattern, -1),
        std::sregex_token_iterator()
    );

    for (auto& section : sections) {
        section = std::regex_replace(section, std::regex("^\\s+|\\s+$"), "");
    }

    return sections;
}

std::vector<std::string> split_by_semicolons_keep_quotes(const std::string& text) {
    std::regex pattern(";\\s*(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)");
    std::vector<std::string> statements(
        std::sregex_token_iterator(text.begin(), text.end(), pattern, -1),
        std::sregex_token_iterator()
    );

    for (auto& statement : statements) {
        statement = std::regex_replace(statement, std::regex("^\\s+|\\s+$"), "");
    }

    return statements;
}

std::vector<std::string> split_by_spaces_keep_quotes(const std::string& text) {
    std::regex pattern("\"(?:\\\\.|[^\"\\\\])*\"[^\\s]*|\"(?:\\\\.|[^\"\\\\])*\"|[^\\s\"]+");
    std::vector<std::string> tokens;
    std::sregex_iterator iter(text.begin(), text.end(), pattern);
    std::sregex_iterator end;

    while (iter != end) {
        tokens.push_back(iter->str());
        ++iter;
    }

    return tokens;
}

std::unordered_map<std::string, std::vector<std::vector<std::string>>> split_by_sections(const std::string& preprocessed_text) {
    std::unordered_map<std::string, std::vector<std::vector<std::string>>> result;
    std::vector<std::string> sections = split_by_periods_keep_quotes(preprocessed_text);

    for (const auto& section : sections) {
        std::vector<std::string> statements = split_by_semicolons_keep_quotes(section);
        std::string subject = split_by_spaces_keep_quotes(statements[0])[0];

        std::vector<std::vector<std::string>> tokenized_statements;
        for (const auto& statement : statements) {
            auto tokens = split_by_spaces_keep_quotes(statement);
            if (tokens[0] == subject) {
                tokens.erase(tokens.begin());
            }
            tokenized_statements.push_back(tokens);
        }

        result[subject] = tokenized_statements;
    }

    return result;
}

void recursive_conversion(const std::unordered_map<std::string, std::vector<std::vector<std::string>>>& sections,
                          const std::string& current_subject,
                          std::vector<std::string>& predicate_chain,
                          std::vector<std::string>& index_chain,
                          std::vector<std::string>& answer) {
    if (sections.find(current_subject) == sections.end()) {
        return;
    }

    for (size_t i = 0; i < sections.at(current_subject).size(); ++i) {
        const auto& triple = sections.at(current_subject)[i];
        std::vector<std::string> new_predicate_chain = predicate_chain;
        std::vector<std::string> new_index_chain = index_chain;
        new_predicate_chain.push_back(triple[0]);
        new_index_chain.push_back(std::to_string(i + 1));

        std::string predicate = std::accumulate(new_predicate_chain.begin(), new_predicate_chain.end(), std::string(),
                                                [](const std::string& a, const std::string& b) {
                                                    return a + (a.empty() ? "" : "|") + b;
                                                });
        std::string index = std::accumulate(new_index_chain.begin(), new_index_chain.end(), std::string(),
                                            [](const std::string& a, const std::string& b) {
                                                return a + (a.empty() ? "" : ",") + b;
                                            });

        for (size_t j = 1; j < triple.size(); ++j) {
            std::string obj = triple[j];
            if (!obj.empty() && obj.back() == ',') {
                obj.pop_back();
            }

            answer.push_back(current_subject + " <" + predicate + ">[" + index + "] " + obj);

            if (sections.find(obj) != sections.end()) {
                recursive_conversion(sections, obj, new_predicate_chain, new_index_chain, answer);
            }
        }
    }
}

std::string convert_to_new_format(const std::unordered_map<std::string, std::vector<std::vector<std::string>>>& sections) {
    std::vector<std::string> answer;

    for (const auto& [subject, triples] : sections) {
        if (std::find(STATEMENT_PREFIX.begin(), STATEMENT_PREFIX.end(), subject.substr(0, 2)) != STATEMENT_PREFIX.end()) {
            continue;
        }

        std::vector<std::string> predicate_chain;
        std::vector<std::string> index_chain;
        recursive_conversion(sections, subject, predicate_chain, index_chain, answer);
    }

    std::sort(answer.begin(), answer.end());
    return std::accumulate(answer.begin(), answer.end(), std::string(),
                           [](const std::string& a, const std::string& b) {
                               return a + (a.empty() ? "" : "\n") + b;
                           });
}

std::string read_file(const std::string& filename) {
    std::ifstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Unable to open file: " + filename);
    }

    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

void write_file(const std::string& filename, const std::string& content) {
    std::ofstream file(filename);
    if (!file.is_open()) {
        throw std::runtime_error("Unable to open file for writing: " + filename);
    }

    file << content;
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <input_file.ttl>" << std::endl;
        return 1;
    }

    std::string input_filename = argv[1];
    std::string output_filename = input_filename + ".converted.txt";

    try {
        auto start_time = std::chrono::high_resolution_clock::now();

        std::cout << "Reading file: " << input_filename << std::endl;
        std::string ttl_text = read_file(input_filename);

        std::cout << "Preprocessing TTL..." << std::endl;
        std::string preprocessed = preprocess_ttl(ttl_text);

        std::cout << "Splitting sections..." << std::endl;
        auto sections = split_by_sections(preprocessed);

        std::cout << "Converting to new format..." << std::endl;
        std::string new_format = convert_to_new_format(sections);

        std::cout << "Writing converted format to: " << output_filename << std::endl;
        write_file(output_filename, new_format);

        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);

        std::cout << "Conversion completed in " << duration.count() << " milliseconds." << std::endl;
        std::cout << "Converted file saved as: " << output_filename << std::endl;
    }
    catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}