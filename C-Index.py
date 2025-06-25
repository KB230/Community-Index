import pandas as pd
import networkx as nx

# ==============================================================================
# SECTION 1: 
# All helper functions and the Author class
# ==============================================================================

def getReciprocal(n, d):
    if n != 0:
        return d/n
    else:
        return 0

class Author(object):
    def __init__(self, paper, first, last, country, country_code, aff_city, gender, specialization):
        self.firstName = first
        self.lastName = last
        self.country = country
        self.country_code = country_code
        self.city = aff_city
        self.gender = gender
        self.paperList = []
        self.specialization = specialization
        if paper:
            self.paperList.append(paper)

    def __eq__(self, other):
        if (isinstance(other, Author)):
            # Using your full equality check
            return (self.firstName == other.firstName and
                    self.lastName == other.lastName and
                    self.gender == other.gender and
                    self.country_code == other.country_code and
                    self.specialization == other.specialization)
        else:
            return False

    def __hash__(self):
        return(hash(self.firstName + self.lastName))

    def getName(self):
        return self.firstName + " " + self.lastName

def collectAuthorsOfOnePaper(df, pub_id, **kwargs):
    refAuthor = kwargs.get('refAuthor', None)
    authorList = []
    # Using your logic to iterate from a start point if provided, but simplifying for general case
    paper_df = df[df['pub_id'] == pub_id]
    for _, row in paper_df.iterrows():
        author = Author(
            row["pub_id"], row["first_name"], row["last_name"],
            row["aff_country"], row["aff_country_code"], row["aff_city"],
            row["gender"], row["specialization"]
        )
        if (author != refAuthor):
            authorList.append(author)
    return authorList

def searchAuthorPapers(df, author):
    paperDict = {}
    author_rows = df[(df['first_name'] == author.firstName) & (df['last_name'] == author.lastName)]
    for pub_id in author_rows['pub_id'].unique():
        authorList = collectAuthorsOfOnePaper(df, pub_id, refAuthor=author)
        clean_pub_id = pub_id.replace("pub.", "")
        paperDict[clean_pub_id] = authorList
    return paperDict

def create_graph(dict_x, **kwargs):
    # Using your original graph creation logic
    refAuthor = kwargs.get('refAuthor', None)
    if refAuthor != None:
        for key in dict_x.keys():
            dict_x[key].append(refAuthor)
    G = nx.from_dict_of_lists(dict_x)
    return G

def binaryCalculation(refAuthorFeature, collabFeature, baseFactor):
    if refAuthorFeature == collabFeature and baseFactor != 0:
        return 1/baseFactor
    else:
        return 0

def processCategoricalCalculation(collabCategory, baseFactor, countDict):
    if collabCategory not in countDict.keys():
        countDict[collabCategory] = baseFactor
    else:
        countDict[collabCategory] += baseFactor

def isWeightedCalculation(authorCategory, categoricalWeights):
    if categoricalWeights is not None:
        weightedCategories = {j for i in categoricalWeights.values() for j in i}
        if authorCategory in list(weightedCategories):
            return True
    return False

# ==============================================================================
# SECTION 2: MINIMALLY MODIFIED calculateDIndex
# I just added a paper_details variable to generate the tables automatically
# I also added the bonus (it was similar to the cost, 
# it just multiplied now by a proportion > 1 
# instead of a proportion < 1 if there is ONLY 1 connection to a collaborator)
# ==============================================================================

def calculateDIndex(author, collabDict, collabGraph, isNew = 1, newBonus = 0.8, **kwargs):
    # This function now returns the final index and a detailed list for reporting.
    crossPaper = kwargs.get('crossPaper', False)
    
    baseGenderFactor = kwargs.get('baseGenderFactor', 1)
    baseNationalityBonus = kwargs.get('baseNationalityBonus', 1)
    baseSpecializationFactor = kwargs.get('baseSpecializationFactor', 1)
    categoricalWeights = kwargs.get('categoricalWeights', None)

    paperFeatureIndices = []
    paper_details_for_reporting = [] # The only addition is this list

    for publication in collabDict.keys():
        genderFactor = 1 * baseGenderFactor
        nationalityBonus = 0
        nationalityCounts = {author.country_code : 1 * baseNationalityBonus}
        specializationFactor = 0
        specializationCounts = {author.specialization : 1 * baseSpecializationFactor}

        for collab in collabDict[publication]:
            bonus = 1
            # Ensuring there is only one connection
            if collabGraph.degree[collab] == isNew and crossPaper == True:
                bonus += newBonus

            genderFactor += binaryCalculation(author.gender, collab.gender, baseGenderFactor*bonus)
            processCategoricalCalculation(collab.country_code,
                                          baseNationalityBonus*bonus,
                                          nationalityCounts)
            processCategoricalCalculation(collab.specialization,
                                          baseSpecializationFactor*bonus,
                                          specializationCounts)

        # Original calculations (nothing changed here)
        final_gender_factor = getReciprocal(genderFactor, len(collabDict[publication]))
        
        nationality_denominator = sum(nationalityCounts.values()) - baseNationalityBonus
        nationality_weight = getReciprocal(nationalityCounts.get(author.country_code, 0), nationality_denominator)
        final_nationality_factor = len(set(nationalityCounts.keys())) * nationality_weight

        specialization_denominator = sum(specializationCounts.values()) - baseSpecializationFactor
        specialization_weight = getReciprocal(specializationCounts.get(author.specialization, 0), specialization_denominator)
        final_specialization_factor = len(set(specializationCounts.keys())) * specialization_weight
        
        if isWeightedCalculation(author.country_code, categoricalWeights):
            final_nationality_factor *= categoricalWeights["nationality"][author.country_code]
        if isWeightedCalculation(author.specialization, categoricalWeights):
            final_specialization_factor *= categoricalWeights["specialization"][author.specialization]

        paper_index = final_gender_factor + final_nationality_factor + final_specialization_factor
        paperFeatureIndices.append(paper_index)

        # Capture the results for this paper for later reporting
        paper_details_for_reporting.append({
            "pub_id": f"pub.{publication}",
            "Gender Factor": final_gender_factor,
            "Nationality Factor": final_nationality_factor,
            "Specialization Factor": final_specialization_factor,
            "Paper Index": paper_index
        })

    final_index = round(sum(paperFeatureIndices) / len(paperFeatureIndices))
    return final_index, paper_details_for_reporting

# ==============================================================================
# SECTION 3: AUTOMATED REPORTING AND DISCOVERY SCRIPTS
# ==============================================================================

def find_best_example_authors(df):
    """
    Analyzes the dataframe to find authors with high and low collaborator repeat rates.
    Returns the names of the best candidates for demonstration.
    """
    unique_authors = df.drop_duplicates(subset=['first_name', 'last_name'])
    author_stats = []
    for _, author_row in unique_authors.iterrows():
        temp_author = Author(None, author_row.first_name, author_row.last_name, None, None, None, None, None)
        papers = searchAuthorPapers(df, temp_author)
        if len(papers) < 2: continue # Focus on authors with multiple papers for better patterns
        all_collaborators = [collab.getName() for sublist in papers.values() for collab in sublist]
        if not all_collaborators: continue
        num_unique_collaborators = len(set(all_collaborators))
        avg_repeat_rate = len(all_collaborators) / num_unique_collaborators
        author_stats.append({"name": temp_author.getName(), "avg_repeat_rate": avg_repeat_rate})

    if not author_stats: return None, None
    sorted_stats = sorted(author_stats, key=lambda x: x['avg_repeat_rate'])
    high_newness_author_name = sorted_stats[0]['name']   # Low repeat rate -> high newness
    high_repeat_author_name = sorted_stats[-1]['name'] # High repeat rate
    return high_repeat_author_name, high_newness_author_name



# ==============================================================================
# SECTION 4: AUTOMATED EXAMPLE AND TABLE GENERATION SCRIPT
# ==============================================================================

def generate_comparison_report(author, df):
    """
    Generates and prints a formatted report for a given author, comparing
    D-Index with and without the cross-paper new author bonus
    """
    print("-" * 95)
    print(f"D-Index Comparison Report for: {author.getName()} ({author.specialization})")
    print("-" * 95)

    papers_dict = searchAuthorPapers(df, author)
    # The graph must be created from the author list *without* the refAuthor for degree to be correct
    graph_for_degree_check = create_graph(papers_dict)

    # --- Run calculations ---
    index_no_bonus, details_no_bonus = calculateDIndex(author, papers_dict, graph_for_degree_check, crossPaper=False)
    index_with_bonus, details_with_bonus = calculateDIndex(author, papers_dict, graph_for_degree_check, crossPaper=True)

    print(f"Overall D-Index (No Bonus): {index_no_bonus}")
    print(f"Overall D-Index (With New Author Bonus): {index_with_bonus}\n")
    print("Detailed Breakdown (Displaying values with bonus applied):")
    header = f"{'Pub ID':<17} | {'Gender':>12} | {'Nationality':>15} | {'Specialization':>16} | {'Paper Index':>15}"
    print(header); print("-" * len(header))
    no_bonus_indices = {d['pub_id']: d['Paper Index'] for d in details_no_bonus}

    for paper_detail in details_with_bonus:
        pub_id = paper_detail['pub_id']
        note = "<- Bonus Applied" if abs(paper_detail['Paper Index'] - no_bonus_indices.get(pub_id, 0)) > 0.01 else ""
        row = (f"{pub_id:<17} | {paper_detail['Gender Factor']:>12.2f} | "
               f"{paper_detail['Nationality Factor']:>15.2f} | {paper_detail['Specialization Factor']:>16.2f} | "
               f"{paper_detail['Paper Index']:>15.2f} {note}")
        print(row)
    print("-" * 95 + "\n")

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    df = pd.read_csv('sampleTableV3.csv')

    print("--- Step 1: Dynamically finding best example authors ---")
    high_repeat_name, high_newness_name = find_best_example_authors(df)

    if not high_repeat_name:
        print("Could not find suitable authors with multiple papers. Exiting.")
    else:
        print(f"Found High-Repeat Author: {high_repeat_name} (Bonus should have less impact)")
        print(f"Found High-Newness Author: {high_newness_name} (Bonus should have more impact)\n")

        print("--- Step 2: Generating reports for these authors ---")

        # --- Process the High-Repeat Author ---
        first_name, last_name = high_repeat_name.split(" ", 1)
        # Find the first paper this author is on to get their full Author object
        author_row = df[(df['first_name'] == first_name) & (df['last_name'] == last_name)].iloc[0]
        authors_on_paper = collectAuthorsOfOnePaper(df, author_row['pub_id'])
        high_repeat_author = next((author for author in authors_on_paper if author.getName() == high_repeat_name), None)
        if high_repeat_author:
            generate_comparison_report(high_repeat_author, df)

        # --- Process the High-Newness Author ---
        first_name, last_name = high_newness_name.split(" ", 1)
        author_row = df[(df['first_name'] == first_name) & (df['last_name'] == last_name)].iloc[0]
        authors_on_paper = collectAuthorsOfOnePaper(df, author_row['pub_id'])
        high_newness_author = next((author for author in authors_on_paper if author.getName() == high_newness_name), None)
        if high_newness_author:
            generate_comparison_report(high_newness_author, df)