from flask import (
    Flask, 
    g, 
    jsonify, 
    render_template, 
    request
)
from neo4j import (
    GraphDatabase
)

url = 'bolt://localhost:7687'
username = 'neo4j'
password = 'test'

app = Flask(__name__)
driver = GraphDatabase.driver(url, auth=(username, password))


def get_db():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db

@app.teardown_appcontext 
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()


def create_author_tx(tx, person, topic):
    return tx.run(
        'MERGE (p:Person { name: $person }) '
        'MERGE (t:Topic { name: $topic }) '
        'MERGE (p)-[:CREATED]->(t) ', 
        person=person, 
        topic=topic
    )

def create_editor_tx(tx, person, topic):
    return tx.run(
        'MERGE (p:Person { name: $person }) '
        'MERGE (t:Topic { name: $topic }) '
        'MERGE (p)-[:EDITED]->(t) ', 
        person=person, 
        topic=topic
    )


with app.app_context():
    db = get_db()

    author_rels = (
        ('Andy', 'JavaScript Development'), 
        ('Andy', 'Python Development'), 
        ('Michael', 'Ruby Development'), 
    )
    for a,b in author_rels: 
        db.write_transaction(create_author_tx, a, b)

    editor_rels = (
        ('Andy', 'JavaScript Development'), 
        ('Michael', 'JavaScript Development'), 
        ('Jennifer', 'JavaScript Development'), 
        ('Andy', 'Python Development'), 
        ('Jennifer', 'Python Development'), 
    )
    for a,b in editor_rels: 
        db.write_transaction(create_editor_tx, a, b)


@app.route('/', methods=['GET', 'POST'])
def index():
    def work(tx, person, topic):
        return tx.run(
            'MATCH (p:Person)-[r]-(t:Topic) '
            'WHERE id(p) = $person AND id(t) = $topic '
            'RETURN p.name AS person_name, type(r) AS type, t.name AS topic_name '
            'ORDER BY p.name, type(r), t.name', 
            person=person, 
            topic=topic
        ).data()
    
    data = []
    if request.method == 'POST':
        db = get_db()
        data = db.read_transaction(
            work, 
            request.form.get('person', 0, type=int), 
            request.form.get('topic', 0, type=int)
        )
    return render_template('index.html', data=data)

@app.route('/topics')
def topics(): 
    def work(tx, qs):
        return tx.run(
            'MATCH (t:Topic) '
            'WHERE toLower(t.name) CONTAINS toLower($qs) '
            'RETURN id(t) AS id, t.name AS text '
            'ORDER BY t.name', 
            qs=qs
        ).data()
    db = get_db()
    data = db.read_transaction(work, request.args.get('q', ''))
    return jsonify(results=data)

@app.route('/persons')
def persons():
    def work(tx, topic, qs):
        return tx.run(
            'MATCH (p:Person)-[]-(t:Topic) '
            'WHERE id(t) = $topic AND toLower(p.name) CONTAINS toLower($qs) '
            'RETURN DISTINCT id(p) AS id, p.name AS text '
            'ORDER By p.name', 
            topic=topic, 
            qs=qs
        ).data()
    db = get_db()
    data = db.read_transaction(
        work, 
        request.args.get('topic', 0, type=int), 
        request.args.get('q', '')
    )
    return jsonify(results=data)
