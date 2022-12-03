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


def create_author_tx(tx, topic, person):
    return tx.run(
        'MERGE (t:Topic { name: $topic }) '
        'MERGE (p:Person { name: $person }) '
        'MERGE (t)-[:CREATED_BY]->(p) ', 
        topic=topic, 
        person=person
    ).single()

def create_editor_tx(tx, topic, person):
    return tx.run(
        'MERGE (t:Topic { name: $topic }) '
        'MERGE (p:Person { name: $person }) '
        'MERGE (t)-[:EDITED_BY]->(p) ', 
        topic=topic, 
        person=person
    ).single()


with app.app_context():
    db = get_db()

    author_rels = (
        ('JavaScript Development', 'Andy'), 
        ('Python Development', 'Andy'), 
        ('Ruby Development', 'Michael'), 
    )
    for a,b in author_rels: 
        db.write_transaction(create_author_tx, a, b)

    editor_rels = (
        ('JavaScript Development', 'Andy'), 
        ('JavaScript Development', 'Michael'), 
        ('JavaScript Development', 'Jennifer'), 
        ('Python Development', 'Andy'), 
        ('Python Development', 'Jennifer'), 
    )
    for a,b in editor_rels: 
        db.write_transaction(create_editor_tx, a, b)

@app.route('/', methods=['GET', 'POST'])
def index():
    def work(tx, topic, person):
        return tx.run(
            'MATCH (t:Topic)-[r]-(p:Person) '
            'WHERE id(t) = $topic AND id(p) = $person '
            'RETURN t.name AS topic_name, type(r) AS type, p.name AS person_name '
            'ORDER BY t.name, type(r), p.name', 
            topic=topic, 
            person=person
        ).data()
    
    data = []
    if request.method == 'POST':
        db = get_db()
        data = db.read_transaction(
            work, 
            request.form.get('topic', 0, type=int), 
            request.form.get('person', 0, type=int)
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
            'MATCH (t:Topic)-[]-(p:Person) '
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
