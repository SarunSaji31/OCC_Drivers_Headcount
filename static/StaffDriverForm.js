class StaffDriverForm extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            staffId: '',
            driverName: '',
            staffIds: []
        };
        this.handleStaffIdChange = this.handleStaffIdChange.bind(this);
    }

    componentDidMount() {
        fetch('/api/staff-ids/')
            .then(response => response.json())
            .then(data => this.setState({ staffIds: data }));
    }

    handleStaffIdChange(event) {
        const staffId = event.target.value;
        this.setState({ staffId });

        fetch(`/api/get-driver-name/?staff_id=${staffId}`)
            .then(response => response.json())
            .then(data => this.setState({ driverName: data.driver_name }));
    }

    render() {
        return (
            <div>
                <div className="form-group">
                    <label htmlFor="staffId">Staff ID</label>
                    <input
                        type="text"
                        className="form-control"
                        id="staffId"
                        value={this.state.staffId}
                        onChange={this.handleStaffIdChange}
                        list="staffIds"
                    />
                    <datalist id="staffIds">
                        {this.state.staffIds.map((id, index) => (
                            <option key={index} value={id} />
                        ))}
                    </datalist>
                </div>
                <div className="form-group">
                    <label htmlFor="driverName">Driver Name</label>
                    <input
                        type="text"
                        className="form-control"
                        id="driverName"
                        value={this.state.driverName}
                        readOnly
                    />
                </div>
            </div>
        );
    }
}

const domContainer = document.querySelector('#staff-driver-form-container');
ReactDOM.render(<StaffDriverForm />, domContainer);
